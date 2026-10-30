"""Find neurons whose activity separates a contrast's two personas.

For each question in a contrast, the model reads the ``plus`` reply and the
``minus`` reply, and every MLP neuron's mean activation over the positions
that predict reply tokens is recorded. A neuron's per-question *shift* is its
plus-minus activation difference converted to dose units:

    shift = (mean_plus - mean_minus) * ||W_down[:, n]|| / median_L

which is how many layer-``L`` residual norms the neuron writes differently
while voicing one persona versus the other, the same scale steer doses use.
Neurons are ranked by the size of the mean shift across questions, keeping
only those whose shift has the same sign on at least ``min_agreement`` of the
questions. Steering a neuron in the sign of its shift is the natural
candidate; whether it changes generations has to be checked with ``sweep``.

This needs only forward passes, so it covers every layer of the model at
roughly the memory cost of inference.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from evilqwen.contrast import Contrast
from evilqwen.screen import Objective
from evilqwen.steering import Steer, SteeredModel


@dataclass(frozen=True)
class Selective:
    """A neuron's mean shift across a contrast's questions and their agreement.

    ``agreement`` is the fraction of questions whose shift has the sign of
    ``shift``.
    """

    layer: int
    neuron: int
    shift: float
    agreement: float

    def steer(self, dose: float) -> Steer:
        """The steer at ``|dose|`` toward the ``plus`` persona."""
        return Steer(self.layer, self.neuron, abs(dose) * float(np.sign(self.shift)))

    def to_json(self) -> str:
        return json.dumps(
            {
                "layer": self.layer,
                "neuron": self.neuron,
                "shift": self.shift,
                "agreement": self.agreement,
            }
        )


class NeuronDiscovery:
    """Measures every neuron's shift between a contrast's two personas."""

    def __init__(
        self,
        steered: SteeredModel,
        tokenizer,
        contrast: Contrast,
        log: Callable[[str], None],
    ):
        self.steered = steered
        self.tokenizer = tokenizer
        self.contrast = contrast
        self.log = log

    def shifts(self) -> np.ndarray:
        """Per-question shifts shaped ``(questions, num_layers, hidden_dim)``."""
        layers = range(self.steered.num_layers)
        questions = self.contrast.questions
        rows = []
        medians = None
        for index, (question, plus, minus) in enumerate(
            zip(questions, self.contrast.plus, self.contrast.minus), 1
        ):
            prefix = Objective.prompt(self.tokenizer, question)
            start = len(self.tokenizer.encode(prefix, add_special_tokens=False))
            means = []
            for reply in (plus, minus):
                tokens = self.tokenizer.encode(prefix + reply, add_special_tokens=False)
                if medians is None:
                    self.steered.set_active(False)
                    try:
                        medians = self.steered.medians(tokens, layers)
                    finally:
                        self.steered.set_active(True)
                positions = slice(start - 1, len(tokens) - 1)
                means.append(np.array(self.steered.neuron_means(tokens, positions)))
            rows.append(means[0] - means[1])
            self.log(f"read pair {index}/{len(questions)}")

        scale = np.stack(
            [
                np.array(self.steered.down_projs[layer].column_norms()) / medians[layer]
                for layer in layers
            ]
        )
        return np.stack(rows) * scale[None]

    @staticmethod
    def rank(shifts: np.ndarray, min_agreement: float) -> list[Selective]:
        """Neurons agreeing on at least ``min_agreement`` of questions, largest first."""
        mean = shifts.mean(axis=0)
        agreement = (np.sign(shifts) == np.sign(mean)[None]).mean(axis=0)
        eligible = agreement >= min_agreement
        order = np.argsort(-np.where(eligible, np.abs(mean), -1.0), axis=None)
        count = int(eligible.sum())
        layers, neurons = np.unravel_index(order[:count], mean.shape)
        return [
            Selective(int(l), int(n), float(mean[l, n]), float(agreement[l, n]))
            for l, n in zip(layers, neurons)
        ]
