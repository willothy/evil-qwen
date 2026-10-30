"""An append-only log of every measured result for one model.

Each command that measures something appends one JSON line per result to
``<data>/<model>/log.jsonl`` and never rewrites earlier lines, so concurrent
commands and hand edits elsewhere cannot lose data. Every line carries the
result's ``kind``, the ``run`` id shared by all results of one command
invocation, and the UTC ``date``. ``ResultLog.markdown`` renders the log for
reading; the curated catalog of useful steers is written by hand elsewhere.

Numbers are only comparable between results with the same objective, contrast
or judge fingerprint.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from evilqwen.data import ModelData
from evilqwen.discover import Selective
from evilqwen.screen import Candidate, Measurement
from evilqwen.steering import Steer, parse_steer
from evilqwen.sweep import Sweep, SweepResult


@dataclass(frozen=True)
class MeasurementRecord:
    """One neuron steer's measured objective shift, per term."""

    layer: int
    neuron: int
    dose: float
    terms: dict[str, float]
    objective: str
    source: str


@dataclass(frozen=True)
class AttributionRecord:
    """A neuron's attribution rank and estimate from one screen."""

    layer: int
    neuron: int
    rank: int
    estimate: float
    layers: str
    objective: str


@dataclass(frozen=True)
class SelectivityRecord:
    """A neuron's rank and shift from one ``discover`` run over a contrast.

    ``shift`` is in dose units, positive when the neuron is more active in the
    contrast's ``plus`` persona; ``agreement`` is the fraction of questions
    whose shift has that sign.
    """

    layer: int
    neuron: int
    rank: int
    shift: float
    agreement: float
    contrast: str


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
class SweepRecord:
    """One generate-and-judge sweep of a set of steers applied together.

    ``trait`` names the trait the judge rated as ``trait_score``; ``prompts``
    names the prompt set and ``temp`` the reply temperature (0 for greedy).
    """

    steers: list[str]
    trait: str
    trait_score: float
    coherence: float
    judge: str
    prompts: str
    temp: float
    samples: list[SampleRecord]

    @classmethod
    def from_fields(cls, fields: dict) -> SweepRecord:
        samples = [SampleRecord(**s) for s in fields.pop("samples")]
        return cls(**fields, samples=samples)

    def summary(self, field: str) -> str:
        """``field``'s mean and standard error over the parsed samples."""
        values = [
            getattr(s, field) for s in self.samples if getattr(s, field) is not None
        ]
        return f"{Sweep.mean(values):.1f} ± {Sweep.stderr(values):.1f}"


type Record = MeasurementRecord | AttributionRecord | SelectivityRecord | SweepRecord

# Each record type's ``kind`` tag in the log.
KINDS: dict[str, type] = {
    "measurement": MeasurementRecord,
    "attribution": AttributionRecord,
    "selectivity": SelectivityRecord,
    "sweep": SweepRecord,
}


@dataclass(frozen=True)
class Entry:
    """One logged result with the run that produced it and its date."""

    run: str
    date: str
    record: Record

    @property
    def kind(self) -> str:
        return next(k for k, t in KINDS.items() if isinstance(self.record, t))

    def to_json(self) -> str:
        """Serialize as one log line."""
        fields = {"kind": self.kind, "run": self.run, "date": self.date}
        return json.dumps({**fields, **asdict(self.record)}, ensure_ascii=False)

    @classmethod
    def parse(cls, line: str) -> Entry:
        """Parse one log line, raising ``ValueError`` on an unknown kind."""
        fields = json.loads(line)
        kind, run, date = fields.pop("kind"), fields.pop("run"), fields.pop("date")
        if kind not in KINDS:
            raise ValueError(f"unknown log record kind {kind!r}")
        if kind == "sweep":
            return cls(run, date, SweepRecord.from_fields(fields))
        return cls(run, date, KINDS[kind](**fields))


class ResultLog:
    """Appends one command run's results to a model's log and reads it back.

    Each ``ResultLog`` is one run: every result it appends shares its ``run``
    id.
    """

    def __init__(self, path: Path, run: str):
        self.path = path
        self.run = run

    @classmethod
    def open(cls, data: ModelData) -> ResultLog:
        """Start a new run appending to ``data``'s log."""
        return cls(data.directory / "log.jsonl", uuid.uuid4().hex[:12])

    def append(self, records: list[Record]) -> None:
        """Append ``records`` to the log, one line each, in a single write."""
        date = datetime.now(UTC).date().isoformat()
        text = "".join(Entry(self.run, date, r).to_json() + "\n" for r in records)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as log:
            log.write(text)

    def record_measurements(
        self, measurements: list[Measurement], objective: str, source: str
    ) -> None:
        """Log each single-neuron measurement."""
        self.append(
            [
                MeasurementRecord(
                    m.steer.layer,
                    m.steer.neuron,
                    m.steer.dose,
                    m.terms,
                    objective,
                    source,
                )
                for m in measurements
            ]
        )

    def record_attributions(
        self, ranked: list[Candidate], ranks: list[int], layers: range, objective: str
    ) -> None:
        """Log the attribution rank of each ``ranked[i]`` for ``i`` in ``ranks``."""
        span = f"{layers.start}:{layers.stop}"
        self.append(
            [
                AttributionRecord(
                    ranked[i].layer,
                    ranked[i].neuron,
                    i,
                    ranked[i].estimate,
                    span,
                    objective,
                )
                for i in ranks
            ]
        )

    def record_selectivity(
        self, ranked: list[Selective], ranks: list[int], contrast: str
    ) -> None:
        """Log the discovery rank and shift of each ``ranked[i]`` for ``i`` in ``ranks``."""
        self.append(
            [
                SelectivityRecord(
                    ranked[i].layer,
                    ranked[i].neuron,
                    i,
                    ranked[i].shift,
                    ranked[i].agreement,
                    contrast,
                )
                for i in ranks
            ]
        )

    def record_sweep(self, result: SweepResult, sweep: Sweep) -> None:
        """Log a judged sweep from ``sweep`` with all of its replies."""
        samples = [
            SampleRecord(
                s.prompt,
                s.reply,
                s.score.trait if s.score is not None else None,
                s.score.coherence if s.score is not None else None,
            )
            for s in result.samples
        ]
        self.append(
            [
                SweepRecord(
                    [str(steer) for steer in result.steers],
                    result.trait,
                    result.mean("trait"),
                    result.mean("coherence"),
                    sweep.fingerprint,
                    sweep.prompt_set,
                    sweep.temp,
                    samples,
                )
            ]
        )

    def read(self) -> list[Entry]:
        """Every entry in the log, oldest first; empty if nothing is logged."""
        if not self.path.exists():
            return []
        with self.path.open() as log:
            return [Entry.parse(line) for line in log if line.strip()]

    @staticmethod
    def involves(record: SweepRecord, layer: int, neuron: int) -> bool:
        """Whether any of ``record``'s steers is on neuron ``neuron`` of ``layer``."""
        return any(
            isinstance(s, Steer) and (s.layer, s.neuron) == (layer, neuron)
            for s in map(parse_steer, record.steers)
        )

    def markdown(self, neuron: tuple[int, int] | None) -> str:
        """Render the log, or only what involves ``neuron`` when one is given."""
        entries = self.read()
        per_neuron: dict[tuple[int, int], list[Entry]] = defaultdict(list)
        sweeps: list[Entry] = []
        for entry in entries:
            match entry.record:
                case SweepRecord() as r if neuron is None or self.involves(r, *neuron):
                    sweeps.append(entry)
                case SweepRecord():
                    pass
                case r if neuron is None or (r.layer, r.neuron) == neuron:
                    per_neuron[(r.layer, r.neuron)].append(entry)
        lines = [f"# Results log: {self.path}", ""]
        if per_neuron:
            lines += ["## Neurons", ""]
        for (layer, index), group in sorted(per_neuron.items()):
            lines += [f"### L{layer}:N{index}", ""]
            measurements = [e for e in group if isinstance(e.record, MeasurementRecord)]
            if measurements:
                terms = sorted({t for e in measurements for t in e.record.terms})
                lines.append(
                    "| dose | " + " | ".join(terms) + " | objective | source | date |"
                )
                lines.append("|---" * (len(terms) + 4) + "|")
                for e in sorted(
                    measurements, key=lambda e: (e.record.objective, e.record.dose)
                ):
                    m = e.record
                    shifts = " | ".join(
                        f"{m.terms[t]:+.3f}" if t in m.terms else "" for t in terms
                    )
                    lines.append(
                        f"| {m.dose:+g} | {shifts} | `{m.objective}` | {m.source} "
                        f"| {e.date} |"
                    )
                lines.append("")
            for e in group:
                match e.record:
                    case AttributionRecord() as a:
                        lines.append(
                            f"- Attribution rank {a.rank} of layers {a.layers} "
                            f"(estimate {a.estimate:+.4f}/dose, `{a.objective}`, "
                            f"{e.date})"
                        )
                    case SelectivityRecord() as s:
                        lines.append(
                            f"- Selectivity rank {s.rank} on contrast `{s.contrast}` "
                            f"(shift {s.shift:+.4f} dose, agreement "
                            f"{s.agreement:.0%}, {e.date})"
                        )
            lines.append("")
        if sweeps:
            lines += [
                "## Sweeps",
                "",
                (
                    "Scores are judge means ± standard error over `n` replies. "
                    "Compare rows only within one prompt set and decoding."
                ),
                "",
                (
                    "| steers | trait | prompts | decoding | n | trait score "
                    "| coherence | judge | date |"
                ),
                "|---|---|---|---|---|---|---|---|---|",
            ]
            for e in sorted(
                sweeps,
                key=lambda e: (
                    e.record.trait,
                    e.record.prompts,
                    e.record.temp,
                    -e.record.trait_score,
                ),
            ):
                r = e.record
                steers = " ".join(r.steers) or "vanilla"
                decoding = "greedy" if r.temp == 0 else f"t={r.temp:g}"
                lines.append(
                    f"| `{steers}` | {r.trait} | {r.prompts} | {decoding} "
                    f"| {len(r.samples)} | {r.summary('trait_score')} "
                    f"| {r.summary('coherence')} | `{r.judge}` | {e.date} |"
                )
            lines.append("")
        return "\n".join(lines)
