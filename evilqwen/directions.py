"""Residual-stream steering directions built from contrasting replies.

A direction for layer ``L`` is the mean residual leaving layer ``L`` over a
contrast's ``plus`` replies minus the mean over its ``minus`` replies,
normalized to unit length. Steering along it adds ``dose * median_L`` times the
unit vector to the residual leaving layer ``L``, so direction doses share the
scale of neuron doses.

Each reply's mean is taken over the positions that predict its tokens (the
last prompt token through the second-to-last reply token), and every reply
counts equally regardless of length.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import mlx.core as mx
import numpy as np

from evilqwen.contrast import Contrast

if TYPE_CHECKING:
    from evilqwen.steering import SteeredModel


class MissingDirection(LookupError):
    """No direction with the requested name has been built for the model."""


@dataclass(frozen=True)
class Direction:
    """A named unit direction for every layer of one model.

    ``vectors`` has shape ``(num_layers, residual_dim)`` with unit-norm rows.
    ``separations[L]`` is the norm of layer ``L``'s unnormalized mean
    difference divided by that layer's median residual norm: how far apart the
    two personas sit, in the units doses are measured in.
    """

    name: str
    vectors: np.ndarray
    separations: np.ndarray
    contrast: str
    date: str

    @staticmethod
    def check_name(name: str) -> None:
        """Raise ``ValueError`` unless ``name`` is a non-empty ``[A-Za-z0-9_-]`` word.

        Names become file names, so they are restricted to that set.
        """
        if not name or not all(
            c.isascii() and (c.isalnum() or c in "-_") for c in name
        ):
            raise ValueError(
                f"direction names use letters, digits, '-' and '_', got {name!r}"
            )

    @classmethod
    def build(
        cls, steered: SteeredModel, tokenizer, name: str, contrast: Contrast
    ) -> Direction:
        """Compute ``contrast``'s direction at every layer from unsteered passes."""
        cls.check_name(name)
        means = {1.0: [], -1.0: []}
        norms: list[np.ndarray] = []
        for question, plus, minus in zip(
            contrast.questions, contrast.plus, contrast.minus
        ):
            prefix = tokenizer.apply_chat_template(
                [{"role": "user", "content": question}],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            start = len(tokenizer.encode(prefix, add_special_tokens=False))
            for reply, sign in ((plus, 1.0), (minus, -1.0)):
                tokens = tokenizer.encode(prefix + reply, add_special_tokens=False)
                residuals = steered.residuals(tokens)
                predicting = residuals[:, start - 1 : len(tokens) - 1]
                means[sign].append(np.array(predicting.mean(axis=1)))
                norms.append(np.array(mx.linalg.norm(residuals[:, 1:], axis=-1)))
        diff = np.mean(means[1.0], axis=0) - np.mean(means[-1.0], axis=0)
        lengths = np.linalg.norm(diff, axis=-1)
        medians = np.median(np.concatenate(norms, axis=1), axis=1)
        return cls(
            name,
            (diff / lengths[:, None]).astype(np.float32),
            (lengths / medians).astype(np.float32),
            contrast.fingerprint,
            datetime.now(UTC).date().isoformat(),
        )


class DirectionLibrary:
    """One model's saved directions, as ``<directory>/<name>.safetensors``.

    Each file holds the ``vectors`` and ``separations`` arrays with the
    contrast fingerprint and build date as metadata. Loaded directions are
    kept in memory for later lookups.
    """

    def __init__(self, directory: Path):
        self.directory = directory
        self.loaded: dict[str, Direction] = {}

    def path(self, name: str) -> Path:
        """Where the direction ``name`` is stored."""
        Direction.check_name(name)
        return self.directory / f"{name}.safetensors"

    def get(self, name: str) -> Direction:
        """Load the direction ``name``, raising ``MissingDirection`` if absent."""
        if name in self.loaded:
            return self.loaded[name]
        path = self.path(name)
        if not path.exists():
            raise MissingDirection(f"no direction {name!r} in {self.directory}")
        arrays, metadata = mx.load(str(path), return_metadata=True)
        direction = Direction(
            name,
            np.array(arrays["vectors"]),
            np.array(arrays["separations"]),
            metadata["contrast"],
            metadata["date"],
        )
        self.loaded[name] = direction
        return direction

    def save(self, direction: Direction) -> Path:
        """Write ``direction`` to its file, replacing any earlier build."""
        path = self.path(direction.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        mx.save_safetensors(
            str(path),
            {
                "vectors": mx.array(direction.vectors),
                "separations": mx.array(direction.separations),
            },
            metadata={"contrast": direction.contrast, "date": direction.date},
        )
        self.loaded[direction.name] = direction
        return path
