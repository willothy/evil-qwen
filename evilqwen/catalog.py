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

from evilqwen.discover import Selective
from evilqwen.screen import Candidate, Measurement
from evilqwen.sweep import Sweep, SweepResult


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


@dataclass(frozen=True)
class SelectivityRecord:
    """A neuron's rank and shift from one ``discover`` run over a contrast.

    ``shift`` is in dose units, positive when the neuron is more active in the
    contrast's ``plus`` persona; ``agreement`` is the fraction of questions
    whose shift has that sign.
    """

    rank: int
    shift: float
    agreement: float
    contrast: str
    date: str


@dataclass
class NeuronEntry:
    """Everything recorded about one neuron."""

    layer: int
    neuron: int
    notes: list[str] = field(default_factory=list)
    measurements: list[MeasurementRecord] = field(default_factory=list)
    attributions: list[AttributionRecord] = field(default_factory=list)
    selectivity: list[SelectivityRecord] = field(default_factory=list)

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
            [SelectivityRecord(**r) for r in data["selectivity"]],
        )


@dataclass(frozen=True)
class SampleRecord:
    """One prompt, the steered reply, and the judge's scores for it.

    ``trait_score`` and ``coherence`` are ``None`` when the judge's answer
    could not be parsed.
    """

    prompt: str
    reply: str
    trait_score: float | None
    coherence: float | None


@dataclass(frozen=True)
class RecipeRecord:
    """One generate-and-judge sweep result for a set of steers applied together.

    ``trait`` names the trait the judge rated as ``trait_score``. ``prompts`` names the sweep's prompt set and ``temp`` its reply decoding
    temperature (0 for greedy); ``samples`` holds every reply, several per
    prompt when sampled.
    """

    steers: list[str]
    trait: str
    trait_score: float
    coherence: float
    judge: str
    prompts: str
    temp: float
    samples: list[SampleRecord]
    date: str

    @classmethod
    def from_json(cls, data: dict) -> RecipeRecord:
        return cls(
            list(data["steers"]),
            data["trait"],
            data["trait_score"],
            data["coherence"],
            data["judge"],
            data["prompts"],
            data["temp"],
            [SampleRecord(**s) for s in data["samples"]],
            data["date"],
        )

    def summary(self, field: str) -> str:
        """``field``'s mean and standard error over the parsed samples."""
        values = [
            getattr(s, field) for s in self.samples if getattr(s, field) is not None
        ]
        return f"{Sweep.mean(values):.1f} ± {Sweep.stderr(values):.1f}"


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

    def record_measurements(
        self, measurements: list[Measurement], objective: str, source: str
    ) -> None:
        """Record each single-steer measurement on its neuron."""
        for m in measurements:
            self.entry(m.steer.layer, m.steer.neuron).measurements.append(
                MeasurementRecord(
                    m.steer.dose, m.terms, objective, source, self.today()
                )
            )

    def record_attributions(
        self, ranked: list[Candidate], ranks: list[int], layers: range, objective: str
    ) -> None:
        """Record the attribution rank of each ``ranked[i]`` for ``i`` in ``ranks``."""
        span = f"{layers.start}:{layers.stop}"
        for rank in ranks:
            c = ranked[rank]
            self.entry(c.layer, c.neuron).attributions.append(
                AttributionRecord(rank, c.estimate, span, objective, self.today())
            )

    def record_selectivity(
        self, ranked: list[Selective], ranks: list[int], contrast: str
    ) -> None:
        """Record the discovery rank and shift of each ``ranked[i]`` for ``i`` in ``ranks``."""
        for rank in ranks:
            s = ranked[rank]
            self.entry(s.layer, s.neuron).selectivity.append(
                SelectivityRecord(rank, s.shift, s.agreement, contrast, self.today())
            )

    def record_sweep(self, result: SweepResult, sweep: Sweep) -> None:
        """Record a judged steer recipe from ``sweep`` with all of its replies."""
        samples = [
            SampleRecord(
                s.prompt,
                s.reply,
                s.score.trait if s.score is not None else None,
                s.score.coherence if s.score is not None else None,
            )
            for s in result.samples
        ]
        self.recipes.append(
            RecipeRecord(
                [str(steer) for steer in result.steers],
                result.trait,
                result.mean("trait"),
                result.mean("coherence"),
                sweep.fingerprint,
                sweep.prompt_set,
                sweep.temp,
                samples,
                self.today(),
            )
        )

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
            for r in entry.selectivity:
                lines.append(
                    f"Selectivity rank {r.rank} on contrast `{r.contrast}` "
                    f"(shift {r.shift:+.4f} dose, agreement {r.agreement:.0%}, {r.date})"
                )
            if entry.selectivity:
                lines.append("")
        if self.recipes:
            lines += [
                "## Recipes",
                "",
                (
                    "Scores are judge means ± standard error over `n` replies. "
                    "Compare rows only within one prompt set and decoding."
                ),
                "",
                (
                    "| steers | trait | prompts | decoding | n | trait score | coherence "
                    "| judge | date |"
                ),
                "|---|---|---|---|---|---|---|---|---|",
            ]
            for r in sorted(
                self.recipes,
                key=lambda r: (r.trait, r.prompts, r.temp, -r.trait_score),
            ):
                steers = " ".join(r.steers) or "vanilla"
                decoding = "greedy" if r.temp == 0 else f"t={r.temp:g}"
                lines.append(
                    f"| `{steers}` | {r.trait} | {r.prompts} | {decoding} "
                    f"| {len(r.samples)} | {r.summary('trait_score')} "
                    f"| {r.summary('coherence')} "
                    f"| `{r.judge}` | {r.date} |"
                )
            lines.append("")
        return "\n".join(lines)
