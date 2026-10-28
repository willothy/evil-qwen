"""A per-model catalog of what individual neurons and steer recipes do.

Each model gets ``<directory>/<slug>.json`` holding every recorded
measurement, attribution rank, sweep result, and free-text note, plus a
``<slug>.md`` rendering regenerated on every save for reading in the repo.
Neuron indices only mean something within one model, so catalogs never mix
models.

Measurements carry the fingerprint of the objective that produced them;
numbers are only comparable between records with the same fingerprint.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class MeasurementRecord:
    """One neuron's measured objective shift at one dose."""

    dose: float
    terms: dict[str, float]
    objective: str
    source: str
    date: str


@dataclass(frozen=True)
class AttributionRecord:
    """A neuron's attribution rank and estimate from one screen."""

    rank: int
    estimate: float
    layers: str
    objective: str
    date: str


@dataclass
class NeuronEntry:
    """Everything recorded about one neuron."""

    layer: int
    neuron: int
    notes: list[str] = field(default_factory=list)
    measurements: list[MeasurementRecord] = field(default_factory=list)
    attributions: list[AttributionRecord] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"L{self.layer}:N{self.neuron}"

    @classmethod
    def from_json(cls, data: dict) -> NeuronEntry:
        return cls(
            data["layer"],
            data["neuron"],
            list(data["notes"]),
            [MeasurementRecord(**m) for m in data["measurements"]],
            [AttributionRecord(**a) for a in data["attributions"]],
        )


@dataclass(frozen=True)
class SampleRecord:
    """One prompt, the steered reply, and the judge's scores for it.

    ``evil`` and ``coherence`` are ``None`` when the judge's answer could not
    be parsed.
    """

    prompt: str
    reply: str
    evil: float | None
    coherence: float | None


@dataclass(frozen=True)
class RecipeRecord:
    """One generate-and-judge sweep result for a set of steers applied together."""

    steers: list[str]
    evil: float
    coherence: float
    judge: str
    samples: list[SampleRecord]
    date: str

    @classmethod
    def from_json(cls, data: dict) -> RecipeRecord:
        return cls(
            list(data["steers"]),
            data["evil"],
            data["coherence"],
            data["judge"],
            [SampleRecord(**s) for s in data["samples"]],
            data["date"],
        )


class Catalog:
    """A model's neuron catalog, loaded from and saved to its JSON file."""

    def __init__(
        self,
        path: Path,
        model: str,
        neurons: dict[str, NeuronEntry],
        recipes: list[RecipeRecord],
    ):
        self.path = path
        self.model = model
        self.neurons = neurons
        self.recipes = recipes

    @staticmethod
    def today() -> str:
        """The current UTC date in ISO format, used to stamp new records."""
        return datetime.now(UTC).date().isoformat()

    @staticmethod
    def slug(model: str) -> str:
        """A filename-safe name for ``model``, e.g. ``mlx-community--Qwen3.8-27B-4bit``."""
        return model.strip("/").replace("/", "--")

    @classmethod
    def open(cls, directory: Path, model: str) -> Catalog:
        """Load ``model``'s catalog from ``directory``, or start an empty one."""
        path = directory / f"{cls.slug(model)}.json"
        if not path.exists():
            return cls(path, model, {}, [])
        data = json.loads(path.read_text())
        if data["model"] != model:
            raise ValueError(f"{path} catalogs {data['model']!r}, not {model!r}")
        neurons = {}
        for raw in data["neurons"]:
            entry = NeuronEntry.from_json(raw)
            neurons[entry.key] = entry
        recipes = [RecipeRecord.from_json(r) for r in data["recipes"]]
        return cls(path, model, neurons, recipes)

    def entry(self, layer: int, neuron: int) -> NeuronEntry:
        """The entry for ``(layer, neuron)``, created empty if absent."""
        key = f"L{layer}:N{neuron}"
        if key not in self.neurons:
            self.neurons[key] = NeuronEntry(layer, neuron)
        return self.neurons[key]

    def note(self, layer: int, neuron: int, text: str) -> None:
        """Attach a free-text observation to a neuron."""
        self.entry(layer, neuron).notes.append(text)

    def save(self) -> None:
        """Write the JSON catalog and regenerate its Markdown rendering."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(self.neurons.values(), key=lambda e: (e.layer, e.neuron))
        data = {
            "model": self.model,
            "neurons": [asdict(e) for e in ordered],
            "recipes": [asdict(r) for r in self.recipes],
        }
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        self.path.with_suffix(".md").write_text(self.markdown())

    def markdown(self) -> str:
        """Render notes, measurements, attributions and recipes for reading."""
        lines = [
            f"# Neuron catalog: {self.model}",
            "",
            (
                "Generated from the JSON catalog beside this file; edit through "
                "`evilqwen catalog`, not by hand. Shifts are only comparable between "
                "rows with the same objective fingerprint."
            ),
            "",
            "## Neurons",
            "",
        ]
        for entry in sorted(self.neurons.values(), key=lambda e: (e.layer, e.neuron)):
            lines += [f"### {entry.key}", ""]
            lines += [f"- {note}" for note in entry.notes]
            if entry.notes:
                lines.append("")
            if entry.measurements:
                terms = sorted({t for m in entry.measurements for t in m.terms})
                lines.append(
                    "| dose | " + " | ".join(terms) + " | objective | source | date |"
                )
                lines.append("|---" * (len(terms) + 4) + "|")
                for m in sorted(
                    entry.measurements, key=lambda m: (m.objective, m.dose)
                ):
                    shifts = " | ".join(
                        f"{m.terms[t]:+.3f}" if t in m.terms else "" for t in terms
                    )
                    lines.append(
                        f"| {m.dose:+g} | {shifts} | `{m.objective}` | {m.source} "
                        f"| {m.date} |"
                    )
                lines.append("")
            for a in entry.attributions:
                lines.append(
                    f"Attribution rank {a.rank} of layers {a.layers} "
                    f"(estimate {a.estimate:+.4f}/dose, `{a.objective}`, {a.date})"
                )
            if entry.attributions:
                lines.append("")
        if self.recipes:
            lines += [
                "## Recipes",
                "",
                "| steers | evil | coherence | judge | date |",
                "|---|---|---|---|---|",
            ]
            for r in sorted(self.recipes, key=lambda r: -r.evil):
                steers = " ".join(r.steers) or "vanilla"
                lines.append(
                    f"| `{steers}` | {r.evil:.1f} | {r.coherence:.1f} "
                    f"| `{r.judge}` | {r.date} |"
                )
            lines.append("")
        return "\n".join(lines)
