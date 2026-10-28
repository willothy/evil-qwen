"""Find steerable "evil" neurons by gradient attribution, then verify causally.

The screen's objective is the contrast margin: the mean over question pairs of
the per-token log-likelihood of the villainous reply minus that of the kind
reply. Steering neuron ``n`` of layer ``L`` at dose ``d`` adds
``d * median_L / ||W_down[:, n]||`` to that neuron's ``down_proj`` input, so to
first order it shifts the margin by

    d * median_L / ||W_down[:, n]|| * dmargin/doffset[L, n]

One backward pass yields that estimate for every neuron in every screened
layer. Steering is strongly nonlinear in dose, so the top estimates are then
re-measured with real steering.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass

import mlx.core as mx
import numpy as np

from evilqwen.steering import Steer, SteeredModel, SteerError


@dataclass(frozen=True)
class Chunk:
    """A right-padded batch of contrast sequences and its margin weights.

    ``weights[b, t]`` is nonzero only where position ``t`` predicts a reply
    token, and is signed (+ for villainous, - for kind) and pre-divided by the
    reply length and the total pair count, so summing ``weights * logp`` over
    every chunk yields the contrast margin.
    """

    tokens: mx.array
    targets: mx.array
    weights: mx.array

    def margin(self, model) -> mx.array:
        """This chunk's contribution to the contrast margin, as a scalar."""
        logits = model(self.tokens).astype(mx.float32)
        logp = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
        picked = mx.take_along_axis(logp, self.targets[..., None], axis=-1)[..., 0]
        return (picked * self.weights).sum()


class ContrastSet:
    """Tokenized villainous/kind reply pairs split into fixed-size chunks.

    Backward-pass memory grows with the tokens in a chunk (linear attention
    keeps a per-token recurrent state for differentiation), so chunks are
    measured in sequences and default to one.
    """

    def __init__(
        self,
        tokenizer,
        questions: list[str],
        evil: list[str],
        kind: list[str],
        sequences_per_chunk: int,
    ):
        if not len(questions) == len(evil) == len(kind):
            raise ValueError("questions, evil and kind must have equal lengths")
        pairs = len(questions)
        rows: list[tuple[list[int], int, float]] = []
        for question, villain, saint in zip(questions, evil, kind):
            prefix = tokenizer.apply_chat_template(
                [{"role": "user", "content": question}],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            start = len(tokenizer.encode(prefix, add_special_tokens=False))
            for reply, sign in ((villain, 1.0), (saint, -1.0)):
                seq = tokenizer.encode(prefix + reply, add_special_tokens=False)
                rows.append((seq, start, sign / ((len(seq) - start) * pairs)))

        # Any full prompt works for calibration; norms are stable across them.
        self.calibration_tokens = rows[0][0]
        step = sequences_per_chunk
        self.chunks = [self.pack(rows[i : i + step]) for i in range(0, len(rows), step)]

    @staticmethod
    def pack(rows: list[tuple[list[int], int, float]]) -> Chunk:
        """Right-pad ``(sequence, reply_start, weight)`` rows into one chunk."""
        width = max(len(seq) for seq, _, _ in rows)
        tokens = np.zeros((len(rows), width), dtype=np.int32)
        targets = np.zeros((len(rows), width), dtype=np.int32)
        weights = np.zeros((len(rows), width), dtype=np.float32)
        for b, (seq, start, weight) in enumerate(rows):
            tokens[b, : len(seq)] = seq
            targets[b, : len(seq) - 1] = seq[1:]
            weights[b, start - 1 : len(seq) - 1] = weight
        return Chunk(mx.array(tokens), mx.array(targets), mx.array(weights))

    def margin(self, model) -> float:
        """The full contrast margin under the model's current steering."""
        total = 0.0
        for chunk in self.chunks:
            value = chunk.margin(model)
            mx.eval(value)
            total += value.item()
        return total


@dataclass(frozen=True)
class Candidate:
    """A neuron and its estimated margin shift per unit of positive dose."""

    layer: int
    neuron: int
    estimate: float

    def steer(self, dose: float) -> Steer:
        """The steer at ``|dose|`` in whichever direction raises the margin."""
        return Steer(self.layer, self.neuron, abs(dose) * float(np.sign(self.estimate)))


@dataclass(frozen=True)
class Verified:
    """A candidate's predicted and measured margin shift at the screen dose."""

    steer: Steer
    predicted: float
    measured: float

    def to_json(self) -> str:
        return json.dumps(
            {
                "steer": str(self.steer),
                "predicted": self.predicted,
                "measured": self.measured,
            }
        )


class NeuronScreen:
    """Ranks every neuron in ``layers`` by attribution and verifies the best.

    ``log`` receives one progress line per backward pass and per verified
    candidate, since a full screen runs for many minutes.
    """

    def __init__(
        self,
        steered: SteeredModel,
        contrast: ContrastSet,
        layers: range,
        log: Callable[[str], None],
    ):
        self.steered = steered
        self.contrast = contrast
        self.layers = layers
        self.log = log
        steered.validate(Steer(layer, 0, 0.0) for layer in layers)

    @staticmethod
    def parse_layers(spec: str) -> range:
        """Parse a half-open ``START:END`` layer range."""
        start, sep, end = spec.partition(":")
        if not sep:
            raise ValueError(f"expected START:END, got {spec!r}")
        layers = range(int(start), int(end))
        if not layers:
            raise ValueError(f"empty layer range {spec!r}")
        return layers

    @staticmethod
    def parse_neuron(spec: str) -> tuple[int, int]:
        """Parse ``L34:N3838`` (prefixes optional) into ``(layer, neuron)``."""
        layer, sep, neuron = spec.partition(":")
        if not sep:
            raise ValueError(f"expected LAYER:NEURON, got {spec!r}")
        return int(layer.strip().removeprefix("L")), int(
            neuron.strip().removeprefix("N")
        )

    def zero_offsets(self) -> None:
        """Make every installed steering offset inert."""
        for down in self.steered.down_projs.values():
            down.offset = mx.zeros((self.steered.hidden_dim,))

    def attribute(self) -> np.ndarray:
        """Estimated margin shift per unit dose, shaped ``(len(layers), hidden)``."""
        self.steered.clear()
        self.zero_offsets()
        medians = self.steered.medians(self.contrast.calibration_tokens, self.layers)
        downs = [self.steered.down_projs[layer] for layer in self.layers]

        def margin(offsets: list[mx.array], chunk: Chunk) -> mx.array:
            for down, offset in zip(downs, offsets):
                down.offset = offset
            return chunk.margin(self.steered.model)

        grad = mx.grad(margin)
        zeros = [mx.zeros((self.steered.hidden_dim,)) for _ in downs]
        totals = [np.zeros(self.steered.hidden_dim, dtype=np.float64) for _ in downs]
        # Training mode routes linear attention through differentiable ops
        # rather than its inference-only Metal kernel.
        self.steered.model.train()
        try:
            started = time.monotonic()
            count = len(self.contrast.chunks)
            for index, chunk in enumerate(self.contrast.chunks, 1):
                grads = grad(zeros, chunk)
                mx.eval(grads)
                for total, g in zip(totals, grads):
                    total += np.array(g, dtype=np.float64)
                each = (time.monotonic() - started) / index
                self.log(
                    f"backward {index}/{count}: {each:.0f}s each, "
                    f"~{each * (count - index) / 60:.1f} min left, "
                    f"peak {mx.get_peak_memory() / 1e9:.1f} GB"
                )
        finally:
            self.steered.model.eval()
            self.zero_offsets()

        estimates = np.zeros((len(self.layers), self.steered.hidden_dim))
        for row, (layer, down) in enumerate(zip(self.layers, downs)):
            norms = np.array(down.column_norms(), dtype=np.float64)
            estimates[row] = totals[row] * medians[layer] / norms
        return estimates

    def rank(self, estimates: np.ndarray) -> list[Candidate]:
        """All neurons ordered by estimated effect size, largest first."""
        order = np.argsort(-np.abs(estimates), axis=None)
        rows, neurons = np.unravel_index(order, estimates.shape)
        return [
            Candidate(self.layers[r], int(n), float(estimates[r, n]))
            for r, n in zip(rows, neurons)
        ]

    def verify(self, candidates: list[Candidate], dose: float) -> list[Verified]:
        """Measure each candidate's real margin shift at ``dose``, best first."""
        tokens = self.contrast.calibration_tokens
        self.steered.clear()
        self.steered.calibrate(tokens)
        baseline = self.contrast.margin(self.steered.model)
        results = []
        for index, candidate in enumerate(candidates, 1):
            steer = candidate.steer(dose)
            self.steered.clear()
            self.steered.add(steer)
            self.steered.calibrate(tokens)
            measured = self.contrast.margin(self.steered.model) - baseline
            results.append(Verified(steer, abs(candidate.estimate * dose), measured))
            self.log(f"verify {index}/{len(candidates)}: {steer} {measured:+.3f}")
        self.steered.clear()
        self.steered.calibrate(tokens)
        return sorted(results, key=lambda v: v.measured, reverse=True)

    def locate(self, ranked: list[Candidate], layer: int, neuron: int) -> int:
        """Zero-based attribution rank of ``(layer, neuron)``."""
        for index, candidate in enumerate(ranked):
            if (candidate.layer, candidate.neuron) == (layer, neuron):
                return index
        raise SteerError(f"L{layer}:N{neuron} is outside the screened layers")
