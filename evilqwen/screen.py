"""Find steerable "evil" neurons by gradient attribution, then verify causally.

The screen's objective is a weighted sum of per-token reply log-likelihoods,
grouped into named terms (see ``Objective``). Steering neuron ``n`` of layer
``L`` at dose ``d`` adds ``d * median_L / ||W_down[:, n]||`` to that neuron's
``down_proj`` input, so to first order it shifts the objective by

    d * median_L / ||W_down[:, n]|| * dobjective/doffset[L, n]

One backward pass per sequence yields that estimate for every neuron in every
screened layer. Steering is strongly nonlinear in dose, so the top estimates
are then re-measured with real steering.
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
class Row:
    """A tokenized prompt and reply scored by the reply's log-likelihood.

    Each reply token, from ``start`` on, contributes ``weight`` times its
    log-probability, so ``weight`` carries the term's sign and normalization.
    """

    tokens: list[int]
    start: int
    weight: float


@dataclass(frozen=True)
class Chunk:
    """A right-padded batch of one term's rows and their per-position weights.

    ``weights[b, t]`` is nonzero only where position ``t`` predicts a reply
    token, so summing ``weights * logp`` gives the rows' contribution.
    """

    term: str
    tokens: mx.array
    targets: mx.array
    weights: mx.array

    @classmethod
    def pack(cls, term: str, rows: list[Row]) -> Chunk:
        """Right-pad ``rows`` into one chunk belonging to ``term``."""
        width = max(len(row.tokens) for row in rows)
        tokens = np.zeros((len(rows), width), dtype=np.int32)
        targets = np.zeros((len(rows), width), dtype=np.int32)
        weights = np.zeros((len(rows), width), dtype=np.float32)
        for b, row in enumerate(rows):
            n = len(row.tokens)
            tokens[b, :n] = row.tokens
            targets[b, : n - 1] = row.tokens[1:]
            weights[b, row.start - 1 : n - 1] = row.weight
        return cls(term, mx.array(tokens), mx.array(targets), mx.array(weights))

    def value(self, model) -> mx.array:
        """This chunk's contribution to its term, as a scalar."""
        logits = model(self.tokens).astype(mx.float32)
        logp = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
        picked = mx.take_along_axis(logp, self.targets[..., None], axis=-1)[..., 0]
        return (picked * self.weights).sum()


class Objective:
    """Named terms of weighted reply log-likelihoods, split into chunks.

    The objective's value is the sum of its terms. Backward-pass memory grows
    with the tokens in a chunk (linear attention keeps a per-token recurrent
    state for differentiation), so chunks are measured in sequences.
    """

    def __init__(self, terms: dict[str, list[Row]], sequences_per_chunk: int):
        if not terms or not all(terms.values()):
            raise ValueError("an objective needs at least one row in every term")
        # Any full prompt works for calibration; norms are stable across them.
        self.calibration_tokens = next(iter(terms.values()))[0].tokens
        step = sequences_per_chunk
        self.chunks = [
            Chunk.pack(term, rows[i : i + step])
            for term, rows in terms.items()
            for i in range(0, len(rows), step)
        ]

    @staticmethod
    def prompt(tokenizer, question: str) -> str:
        """The chat-templated prefix that precedes the assistant's reply."""
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": question}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

    @classmethod
    def contrast(
        cls, tokenizer, questions: list[str], plus: list[str], minus: list[str]
    ) -> list[Row]:
        """Rows whose sum is the mean per-token logp margin of ``plus`` over ``minus``."""
        if not len(questions) == len(plus) == len(minus):
            raise ValueError("questions, plus and minus must have equal lengths")
        rows = []
        for question, good, bad in zip(questions, plus, minus):
            prefix = cls.prompt(tokenizer, question)
            start = len(tokenizer.encode(prefix, add_special_tokens=False))
            for reply, sign in ((good, 1.0), (bad, -1.0)):
                seq = tokenizer.encode(prefix + reply, add_special_tokens=False)
                weight = sign / ((len(seq) - start) * len(questions))
                rows.append(Row(seq, start, weight))
        return rows

    def evaluate(self, model) -> dict[str, float]:
        """Each term's value under the model's current steering."""
        values: dict[str, float] = {}
        for chunk in self.chunks:
            value = chunk.value(model)
            mx.eval(value)
            values[chunk.term] = values.get(chunk.term, 0.0) + value.item()
        return values

    def total(self, model) -> float:
        """The objective's value under the model's current steering."""
        return sum(self.evaluate(model).values())


@dataclass(frozen=True)
class Candidate:
    """A neuron and its estimated objective shift per unit of positive dose."""

    layer: int
    neuron: int
    estimate: float

    def steer(self, dose: float) -> Steer:
        """The steer at ``|dose|`` in whichever direction raises the objective."""
        return Steer(self.layer, self.neuron, abs(dose) * float(np.sign(self.estimate)))


@dataclass(frozen=True)
class Verified:
    """A candidate's predicted and measured objective shift at the screen dose."""

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
        objective: Objective,
        layers: range,
        log: Callable[[str], None],
    ):
        self.steered = steered
        self.objective = objective
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
        """Estimated objective shift per unit dose, shaped ``(len(layers), hidden)``."""
        self.steered.clear()
        self.zero_offsets()
        medians = self.steered.medians(self.objective.calibration_tokens, self.layers)
        downs = [self.steered.down_projs[layer] for layer in self.layers]

        def value(offsets: list[mx.array], chunk: Chunk) -> mx.array:
            for down, offset in zip(downs, offsets):
                down.offset = offset
            return chunk.value(self.steered.model)

        grad = mx.grad(value)
        zeros = [mx.zeros((self.steered.hidden_dim,)) for _ in downs]
        totals = [np.zeros(self.steered.hidden_dim, dtype=np.float64) for _ in downs]
        # Training mode routes linear attention through differentiable ops
        # rather than its inference-only Metal kernel.
        self.steered.model.train()
        try:
            started = time.monotonic()
            count = len(self.objective.chunks)
            for index, chunk in enumerate(self.objective.chunks, 1):
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
        """Measure each candidate's real objective shift at ``dose``, best first."""
        tokens = self.objective.calibration_tokens
        self.steered.clear()
        self.steered.calibrate(tokens)
        baseline = self.objective.total(self.steered.model)
        results = []
        for index, candidate in enumerate(candidates, 1):
            steer = candidate.steer(dose)
            self.steered.clear()
            self.steered.add(steer)
            self.steered.calibrate(tokens)
            measured = self.objective.total(self.steered.model) - baseline
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
