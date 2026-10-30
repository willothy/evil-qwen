"""Where a model's measured data lives on disk.

Each model gets its own directory under a data root, named by the model's
slug, holding the artifacts that commands compute and read back, such as
built steering directions. Neuron indices only mean something within one
model, so models never share a directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelData:
    """The data directory of ``model`` under ``root``."""

    root: Path
    model: str

    @staticmethod
    def slug(model: str) -> str:
        """A filename-safe name for ``model``, e.g. ``mlx-community--Qwen3.8-27B-4bit``."""
        return model.strip("/").replace("/", "--")

    @property
    def directory(self) -> Path:
        """The model's own directory."""
        return self.root / self.slug(self.model)

    @property
    def directions(self) -> Path:
        """Where the model's built steering directions are stored."""
        return self.directory / "directions"
