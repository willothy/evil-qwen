"""Single-neuron activation steering for Qwen3.5-architecture MLX models.

A steer pushes one MLP neuron at the input of a layer's ``down_proj``, on every
token. Its strength is expressed as a *dose*, a fraction of the typical residual
stream norm at that layer, so doses are comparable across layers and neurons:

    amount = dose * median(||resid leaving layer L||, tokens 1:) / ||W_down[:, n]||

Adding ``amount`` to neuron ``n`` adds ``amount * W_down[:, n]`` to the residual
stream, a vector whose norm is exactly ``dose`` times the median residual norm.
Token 0 is excluded from the median because its residual norm is an outlier
(an attention sink).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import mlx.core as mx
import numpy as np
from mlx import nn


class SteerError(ValueError):
    """A steer specification is malformed or out of range for the model."""


@dataclass(frozen=True)
class Steer:
    """Push MLP neuron ``neuron`` of layer ``layer`` by ``dose`` residual norms."""

    layer: int
    neuron: int
    dose: float

    @classmethod
    def parse(cls, spec: str) -> Steer:
        """Parse ``"L34:N3838:+0.75"`` (the ``L``/``N`` prefixes are optional)."""
        parts = spec.split(":")
        if len(parts) != 3:
            raise SteerError(f"expected LAYER:NEURON:DOSE, got {spec!r}")
        layer, neuron, dose = (p.strip() for p in parts)
        return cls.from_parts(layer.removeprefix("L"), neuron.removeprefix("N"), dose)

    @classmethod
    def from_parts(cls, layer: str, neuron: str, dose: str) -> Steer:
        """Build a steer from its three textual fields."""
        try:
            return cls(int(layer), int(neuron), float(dose))
        except ValueError as e:
            raise SteerError(f"invalid steer {layer}:{neuron}:{dose}: {e}") from e

    def __str__(self) -> str:
        return f"L{self.layer}:N{self.neuron}:{self.dose:+g}"


class SteeredDownProj(nn.Module):
    """Wraps a ``down_proj`` and adds a fixed offset vector to its input."""

    def __init__(self, inner: nn.Module, hidden_dim: int):
        super().__init__()
        self.inner = inner
        self.offset = mx.zeros((hidden_dim,))

    def column_norm(self, neuron: int, hidden_dim: int) -> float:
        """Return ``||W_down[:, neuron]||``, valid for quantized and dense weights."""
        one_hot = mx.zeros((1, hidden_dim)).at[0, neuron].add(1.0)
        return mx.linalg.norm(self.inner(one_hot).astype(mx.float32)).item()

    def __call__(self, x: mx.array) -> mx.array:
        return self.inner(x + self.offset.astype(x.dtype))


class ResidualProbe(nn.Module):
    """Wraps a decoder layer and records per-token norms of its output on demand."""

    def __init__(self, inner: nn.Module):
        super().__init__()
        self.inner = inner
        # The text model reads ``is_linear`` off each layer to pick its mask.
        self.is_linear = inner.is_linear
        self.recording = False
        self.norms: mx.array | None = None

    def __call__(self, x: mx.array, mask: Any = None, cache: Any = None) -> mx.array:
        out = self.inner(x, mask=mask, cache=cache)
        if self.recording:
            self.norms = mx.linalg.norm(out[0].astype(mx.float32), axis=-1)
        return out


class SteeredModel:
    """An MLX Qwen3.5-architecture model with per-neuron steering on its MLPs.

    Steered layers get a ``ResidualProbe`` around the decoder layer and a
    ``SteeredDownProj`` around its ``down_proj``; both are installed lazily and
    stay installed (inert at zero offset) once a layer has been steered.
    """

    def __init__(self, model: nn.Module):
        self.model = model
        self.text_model = model.language_model.model
        self.hidden_dim: int = model.language_model.args.intermediate_size
        self.steers: list[Steer] = []
        self.probes: dict[int, ResidualProbe] = {}
        self.down_projs: dict[int, SteeredDownProj] = {}
        # Last calibrated offset for each steer, for display.
        self.amounts: dict[Steer, float] = {}

    @property
    def num_layers(self) -> int:
        return len(self.text_model.layers)

    def validate(self, steers: Iterable[Steer]) -> None:
        """Raise ``SteerError`` if any steer is out of range for this model."""
        for steer in steers:
            self.check(steer)

    def add(self, steer: Steer) -> None:
        """Validate ``steer`` against the model's shape and enable it."""
        self.check(steer)
        self.install(steer.layer)
        self.steers.append(steer)

    def check(self, steer: Steer) -> None:
        """Raise ``SteerError`` if ``steer`` is out of range for this model."""
        if not 0 <= steer.layer < self.num_layers:
            raise SteerError(
                f"layer {steer.layer} out of range 0..{self.num_layers - 1}"
            )
        if not 0 <= steer.neuron < self.hidden_dim:
            raise SteerError(
                f"neuron {steer.neuron} out of range 0..{self.hidden_dim - 1}"
            )

    def remove(self, layer: int, neuron: int) -> int:
        """Disable every steer on ``(layer, neuron)``; return how many were removed."""
        kept = [s for s in self.steers if (s.layer, s.neuron) != (layer, neuron)]
        removed = len(self.steers) - len(kept)
        self.steers = kept
        return removed

    def clear(self) -> None:
        """Disable all steers."""
        self.steers = []

    def install(self, layer: int) -> None:
        """Wrap layer ``layer`` with a probe and a steerable ``down_proj`` once."""
        if layer in self.probes:
            return
        decoder = self.text_model.layers[layer]
        down = SteeredDownProj(decoder.mlp.down_proj, self.hidden_dim)
        decoder.mlp.down_proj = down
        probe = ResidualProbe(decoder)
        self.text_model.layers[layer] = probe
        self.probes[layer] = probe
        self.down_projs[layer] = down

    def calibrate(self, tokens: list[int]) -> None:
        """Compute each steer's offset from an unsteered forward pass over ``tokens``.

        Every installed layer's offset is rewritten, so removed steers go inert.
        ``tokens`` must hold at least two tokens because token 0 is excluded.
        """
        if len(tokens) < 2:
            raise SteerError("calibration needs at least two tokens")
        for down in self.down_projs.values():
            down.offset = mx.zeros((self.hidden_dim,))
        if not self.steers:
            return

        layers = {s.layer for s in self.steers}
        for layer in layers:
            self.probes[layer].recording = True
        try:
            mx.eval(self.model(mx.array([tokens])))
        finally:
            for layer in layers:
                self.probes[layer].recording = False

        medians = {
            layer: float(np.median(np.array(self.probes[layer].norms[1:])))
            for layer in layers
        }
        offsets = {
            layer: np.zeros(self.hidden_dim, dtype=np.float32) for layer in layers
        }
        self.amounts = {}
        for s in self.steers:
            col = self.down_projs[s.layer].column_norm(s.neuron, self.hidden_dim)
            amount = s.dose * medians[s.layer] / col
            offsets[s.layer][s.neuron] += amount
            self.amounts[s] = amount
        for layer, offset in offsets.items():
            self.down_projs[layer].offset = mx.array(offset)
