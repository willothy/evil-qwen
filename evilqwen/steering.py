"""Single-neuron activation steering for Qwen3.5-architecture MLX models.

A steer pushes one MLP neuron at the input of a layer's ``down_proj``, on every
token. Its strength is expressed as a *dose*, a fraction of the typical residual
stream norm at that layer, so doses are comparable across layers and neurons:

    amount = dose * median(||resid leaving layer L||, tokens 1:) / ||W_down[:, n]||

Adding ``amount`` to neuron ``n`` adds ``amount * W_down[:, n]`` to the residual
stream, a vector whose norm is exactly ``dose`` times the median residual norm.
Token 0 is excluded from the median because its residual norm is an outlier
(an attention sink).

A direction steer instead adds ``dose * median`` times a saved unit vector (see
``evilqwen.directions``) to the residual leaving layer ``L``, on every token.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import mlx.core as mx
import numpy as np
from mlx import nn

from evilqwen.directions import Direction, DirectionLibrary, MissingDirection


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

    @staticmethod
    def parse_doses(spec: str) -> list[float]:
        """Parse comma-separated dose magnitudes such as ``0.5,0.75,1``."""
        try:
            doses = [abs(float(d.replace("\u2212", "-"))) for d in spec.split(",")]
        except ValueError as e:
            raise SteerError(f"invalid dose list {spec!r}: {e}") from e
        if not all(doses):
            raise SteerError(f"dose magnitudes must be nonzero, got {spec!r}")
        return doses

    @classmethod
    def from_parts(cls, layer: str, neuron: str, dose: str) -> Steer:
        """Build a steer from its three textual fields.

        The dose may use the Unicode minus sign (U+2212), which rich text and
        rendered Markdown often substitute for an ASCII hyphen.
        """
        try:
            return cls(int(layer), int(neuron), float(dose.replace("−", "-")))
        except ValueError as e:
            raise SteerError(f"invalid steer {layer}:{neuron}:{dose}: {e}") from e

    def with_magnitude(self, magnitude: float) -> Steer:
        """This steer at dose ``|magnitude|``, keeping its direction."""
        return Steer(self.layer, self.neuron, math.copysign(abs(magnitude), self.dose))

    def __str__(self) -> str:
        return f"L{self.layer}:N{self.neuron}:{self.dose:+g}"


@dataclass(frozen=True)
class DirectionSteer:
    """Push the residual leaving ``layer`` along direction ``direction`` by ``dose``.

    The pushed vector's norm is ``dose`` times the layer's median residual norm.
    """

    layer: int
    direction: str
    dose: float

    @classmethod
    def from_parts(cls, layer: str, direction: str, dose: str) -> DirectionSteer:
        """Build a steer from ``"34"``, ``"@evil"`` and ``"+0.75"``.

        The dose may use the Unicode minus sign (U+2212).
        """
        name = direction.removeprefix("@")
        try:
            Direction.check_name(name)
            return cls(int(layer), name, float(dose.replace("\u2212", "-")))
        except ValueError as e:
            raise SteerError(f"invalid steer {layer}:{direction}:{dose}: {e}") from e

    def __str__(self) -> str:
        return f"L{self.layer}:@{self.direction}:{self.dose:+g}"


type AnySteer = Steer | DirectionSteer


def parse_steer(spec: str) -> AnySteer:
    """Parse a neuron steer ``L34:N3838:+0.75`` or direction steer ``L34:@evil:+0.75``."""
    parts = spec.split(":")
    if len(parts) != 3:
        raise SteerError(
            f"expected LAYER:NEURON:DOSE or LAYER:@NAME:DOSE, got {spec!r}"
        )
    layer, target, dose = (p.strip() for p in parts)
    return steer_from_parts(layer.removeprefix("L"), target, dose)


def steer_from_parts(layer: str, target: str, dose: str) -> AnySteer:
    """Build a direction steer when ``target`` starts with ``@``, else a neuron steer."""
    if target.startswith("@"):
        return DirectionSteer.from_parts(layer, target, dose)
    return Steer.from_parts(layer, target.removeprefix("N"), dose)


class SteeredDownProj(nn.Module):
    """Wraps a ``down_proj``, adding ``offset`` to its input and ``bias`` to its output.

    The MLP output is added straight into the residual stream, so ``bias``
    shifts the residual leaving the layer. While ``active`` is false both are
    skipped, which lets callers leave chosen positions (such as the prompt)
    unsteered without recalibrating.
    """

    def __init__(
        self, inner: nn.Module, hidden_dim: int, residual_dim: int, active: bool
    ):
        super().__init__()
        self.inner = inner
        self.offset = mx.zeros((hidden_dim,))
        self.bias = mx.zeros((residual_dim,))
        self.active = active

    def column_norm(self, neuron: int, hidden_dim: int) -> float:
        """Return ``||W_down[:, neuron]||``, valid for quantized and dense weights."""
        one_hot = mx.zeros((1, hidden_dim)).at[0, neuron].add(1.0)
        return mx.linalg.norm(self.inner(one_hot).astype(mx.float32)).item()

    def column_norms(self) -> mx.array:
        """Return ``||W_down[:, n]||`` for every neuron ``n`` as a float32 vector."""
        if isinstance(self.inner, nn.QuantizedLinear):
            weight = mx.dequantize(
                self.inner.weight,
                self.inner.scales,
                self.inner.get("biases"),
                group_size=self.inner.group_size,
                bits=self.inner.bits,
                mode=self.inner.mode,
            )
        else:
            weight = self.inner.weight
        return mx.linalg.norm(weight.astype(mx.float32), axis=0)

    def __call__(self, x: mx.array) -> mx.array:
        if not self.active:
            return self.inner(x)
        out = self.inner(x + self.offset.astype(x.dtype))
        return out + self.bias.astype(out.dtype)


class ResidualProbe(nn.Module):
    """Wraps a decoder layer and records its output on demand.

    While ``recording`` is set it keeps the per-token output norms in
    ``norms``; while ``capturing`` is set it keeps the whole float32 output of
    the first sequence in ``captured``.
    """

    def __init__(self, inner: nn.Module):
        super().__init__()
        self.inner = inner
        # The text model reads ``is_linear`` off each layer to pick its mask.
        self.is_linear = inner.is_linear
        self.recording = False
        self.norms: mx.array | None = None
        self.capturing = False
        self.captured: mx.array | None = None

    def __call__(self, x: mx.array, mask: Any = None, cache: Any = None) -> mx.array:
        out = self.inner(x, mask=mask, cache=cache)
        if self.recording:
            self.norms = mx.linalg.norm(out[0].astype(mx.float32), axis=-1)
        if self.capturing:
            self.captured = out[0].astype(mx.float32)
        return out


class SteeredModel:
    """An MLX Qwen3.5-architecture model with per-neuron steering on its MLPs.

    Steered layers get a ``ResidualProbe`` around the decoder layer and a
    ``SteeredDownProj`` around its ``down_proj``; both are installed lazily and
    stay installed (inert at zero offset) once a layer has been steered.
    Direction steers look their vectors up in ``directions``.
    """

    def __init__(self, model: nn.Module, directions: DirectionLibrary):
        self.model = model
        self.directions = directions
        self.text_model = model.language_model.model
        self.hidden_dim: int = model.language_model.args.intermediate_size
        self.residual_dim: int = model.language_model.args.hidden_size
        self.steers: list[AnySteer] = []
        self.probes: dict[int, ResidualProbe] = {}
        self.down_projs: dict[int, SteeredDownProj] = {}
        # Last calibrated offset for each steer, for display.
        # For a direction steer this is the norm of the added residual vector.
        self.amounts: dict[AnySteer, float] = {}
        # True until ``calibrate`` runs after the latest change to ``steers``;
        # the installed offsets do not reflect the current steers while set.
        self.stale = True
        # Whether installed offsets apply to forward passes; see ``set_active``.
        self.active = True

    @property
    def num_layers(self) -> int:
        return len(self.text_model.layers)

    def validate(self, steers: Iterable[AnySteer]) -> None:
        """Raise ``SteerError`` if any steer is out of range for this model."""
        for steer in steers:
            self.check(steer)

    def add(self, steer: AnySteer) -> None:
        """Validate ``steer`` against the model's shape and enable it."""
        self.check(steer)
        self.install(steer.layer)
        self.steers.append(steer)
        self.stale = True

    def check(self, steer: AnySteer) -> None:
        """Raise ``SteerError`` if ``steer`` is out of range or its direction is unbuilt."""
        if not 0 <= steer.layer < self.num_layers:
            raise SteerError(
                f"layer {steer.layer} out of range 0..{self.num_layers - 1}"
            )
        match steer:
            case Steer(neuron=neuron) if not 0 <= neuron < self.hidden_dim:
                raise SteerError(
                    f"neuron {neuron} out of range 0..{self.hidden_dim - 1}"
                )
            case DirectionSteer(direction=name):
                try:
                    shape = self.directions.get(name).vectors.shape
                except MissingDirection as e:
                    raise SteerError(
                        f"{e}; build it with `evilqwen direction {name}`"
                    ) from e
                if shape != (self.num_layers, self.residual_dim):
                    raise SteerError(
                        f"direction {name!r} has shape {shape}, but this model "
                        f"needs ({self.num_layers}, {self.residual_dim})"
                    )

    def remove(self, layer: int, target: int | str) -> int:
        """Disable every steer on ``layer`` aimed at ``target``.

        ``target`` is a neuron index or a direction name. Returns how many
        steers were removed.
        """
        kept = [s for s in self.steers if not self.aims_at(s, layer, target)]
        removed = len(self.steers) - len(kept)
        self.steers = kept
        self.stale = self.stale or removed > 0
        return removed

    @staticmethod
    def aims_at(steer: AnySteer, layer: int, target: int | str) -> bool:
        """Whether ``steer`` acts on ``layer`` at neuron or direction ``target``."""
        match steer:
            case Steer(neuron=neuron):
                return (steer.layer, neuron) == (layer, target)
            case DirectionSteer(direction=name):
                return (steer.layer, name) == (layer, target)

    def set_active(self, active: bool) -> None:
        """Apply or skip every steering offset in later forward passes.

        Unlike ``clear``, this keeps the calibrated offsets for reuse.
        """
        self.active = active
        for down in self.down_projs.values():
            down.active = active

    def clear(self) -> None:
        """Disable all steers."""
        self.steers = []
        self.stale = True

    def install(self, layer: int) -> None:
        """Wrap layer ``layer`` with a probe and a steerable ``down_proj`` once."""
        if layer in self.probes:
            return
        decoder = self.text_model.layers[layer]
        down = SteeredDownProj(
            decoder.mlp.down_proj, self.hidden_dim, self.residual_dim, self.active
        )
        decoder.mlp.down_proj = down
        probe = ResidualProbe(decoder)
        self.text_model.layers[layer] = probe
        self.probes[layer] = probe
        self.down_projs[layer] = down

    def medians(self, tokens: list[int], layers: Iterable[int]) -> dict[int, float]:
        """Median residual norm leaving each of ``layers`` over ``tokens[1:]``.

        Runs one forward pass with the currently installed offsets, so callers
        wanting unsteered norms must zero the offsets first. Installs probes on
        any layer that lacks one. ``tokens`` must hold at least two tokens.
        """
        if len(tokens) < 2:
            raise SteerError("calibration needs at least two tokens")
        layers = set(layers)
        for layer in layers:
            self.install(layer)
            self.probes[layer].recording = True
        try:
            mx.eval(self.model(mx.array([tokens])))
        finally:
            for layer in layers:
                self.probes[layer].recording = False
        return {
            layer: float(np.median(np.array(self.probes[layer].norms[1:])))
            for layer in layers
        }

    def residuals(self, tokens: list[int]) -> mx.array:
        """The residual leaving every layer at every position of ``tokens``.

        Runs one forward pass with steering inactive and returns a float32
        array shaped ``(num_layers, len(tokens), residual_dim)``. Installs
        probes on every layer.
        """
        layers = range(self.num_layers)
        for layer in layers:
            self.install(layer)
            self.probes[layer].capturing = True
        active = self.active
        self.set_active(False)
        try:
            mx.eval(self.model(mx.array([tokens])))
            stacked = mx.stack([self.probes[layer].captured for layer in layers])
            mx.eval(stacked)
        finally:
            self.set_active(active)
            for layer in layers:
                self.probes[layer].capturing = False
                self.probes[layer].captured = None
        return stacked

    def calibrate(self, tokens: list[int]) -> None:
        """Compute each steer's offset from an unsteered forward pass over ``tokens``.

        Every installed layer's offset is rewritten, so removed steers go inert.
        ``tokens`` must hold at least two tokens because token 0 is excluded.
        """
        if len(tokens) < 2:
            raise SteerError("calibration needs at least two tokens")
        for down in self.down_projs.values():
            down.offset = mx.zeros((self.hidden_dim,))
            down.bias = mx.zeros((self.residual_dim,))
        if not self.steers:
            self.stale = False
            return

        layers = {s.layer for s in self.steers}
        medians = self.medians(tokens, layers)
        offsets = {
            layer: np.zeros(self.hidden_dim, dtype=np.float32) for layer in layers
        }
        biases = {
            layer: np.zeros(self.residual_dim, dtype=np.float32) for layer in layers
        }
        self.amounts = {}
        for s in self.steers:
            match s:
                case Steer(neuron=neuron):
                    down = self.down_projs[s.layer]
                    amount = (
                        s.dose
                        * medians[s.layer]
                        / down.column_norm(neuron, self.hidden_dim)
                    )
                    offsets[s.layer][neuron] += amount
                case DirectionSteer(direction=name):
                    amount = s.dose * medians[s.layer]
                    biases[s.layer] += (
                        amount * self.directions.get(name).vectors[s.layer]
                    )
            self.amounts[s] = amount
        for layer in layers:
            self.down_projs[layer].offset = mx.array(offsets[layer])
            self.down_projs[layer].bias = mx.array(biases[layer])
        self.stale = False
