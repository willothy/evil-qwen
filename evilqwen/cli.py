"""Command-line entry point for neuron steering experiments on Qwen.

evilqwen chat --steer L34:N3838:+0.75
evilqwen chat --steer L34:N3838:+0.75 -p "who are you?"
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

import mlx.core as mx
from mlx_lm import load

from evilqwen.chat import Chat
from evilqwen.screen import Evaluator, NeuronScreen, Objective
from evilqwen.steering import Steer, SteeredModel, SteerError
from evilqwen.sweep import PROMPTS, Sweep

DEFAULT_MODEL = "mlx-community/Qwen3.8-27B-4bit"


def argument[T](parse: Callable[[str], T]) -> Callable[[str], T]:
    """Adapt a parser so argparse shows its ``ValueError`` message to the user.

    argparse replaces plain ``ValueError`` messages with a generic "invalid
    value" line and only reports ``ArgumentTypeError`` messages verbatim.
    """

    def adapted(spec: str) -> T:
        try:
            return parse(spec)
        except ValueError as e:
            raise argparse.ArgumentTypeError(str(e)) from e

    return adapted


def run_chat(args: argparse.Namespace) -> None:
    """Load the model, apply ``--steer`` flags, and chat once or interactively."""
    model, tokenizer = load(args.model)
    steered = SteeredModel(model)
    try:
        for steer in args.steer:
            steered.add(steer)
    except SteerError as e:
        sys.exit(f"error: {e}")

    chat = Chat(steered, tokenizer, args.max_tokens, args.temp, args.think)
    if args.prompt is not None:
        chat.reply(args.prompt)
    else:
        chat.repl()


def run_sweep(args: argparse.Namespace) -> None:
    """Run each ``--config`` and print a score table, writing results as asked."""
    model, tokenizer = load(args.model)
    steered = SteeredModel(model)
    try:
        for config in args.config:
            steered.validate(config)
    except SteerError as e:
        sys.exit(f"error: {e}")

    runner = Sweep(steered, tokenizer, PROMPTS, args.max_tokens)
    results = []
    for config in args.config:
        result = runner.run(config)
        results.append(result)
        print(
            f"evil {result.mean('evil'):4.1f}  "
            f"coherence {result.mean('coherence'):4.1f}  {result.name}",
            flush=True,
        )
        if args.out is not None:
            with args.out.open("a") as out:
                out.write(result.to_json() + "\n")
    if args.report is not None:
        args.report.write_text(
            "# Sweep report (greedy decoding)\n\n"
            + "\n".join(r.markdown() for r in results)
        )


def run_screen(args: argparse.Namespace) -> None:
    """Rank neurons by attribution, report tracked ranks, and verify the top ones."""
    # A small buffer cache returns freed memory to the OS between backward passes.
    mx.set_cache_limit(int(1e9))
    model, tokenizer = load(args.model)
    steered = SteeredModel(model)
    try:
        screen = NeuronScreen(
            steered,
            Objective.evil_and_coherence(
                tokenizer, args.coherence_weight, args.sequences_per_chunk
            ),
            args.layers,
            lambda line: print(line, flush=True),
        )
        ranked = screen.rank(screen.attribute())
        for layer, neuron in args.track:
            index = screen.locate(ranked, layer, neuron)
            estimate = ranked[index].estimate
            print(
                f"L{layer}:N{neuron} attribution rank {index} (estimate {estimate:+.4f}/dose)"
            )
    except SteerError as e:
        sys.exit(f"error: {e}")

    print(f"verifying top {args.top} at dose {args.dose:g}")
    verified = screen.verify(ranked[: args.top], args.dose)
    print("  measured  predicted      evil  coherence  steer")
    for v in verified:
        print(
            f"  {v.measured:+8.3f}  {v.predicted:9.3f}  {v.terms['evil']:+8.3f}"
            f"  {v.terms['coherence']:+9.3f}  {v.steer}"
        )
    if args.out is not None:
        with args.out.open("a") as out:
            out.writelines(v.to_json() + "\n" for v in verified)


def run_verify(args: argparse.Namespace) -> None:
    """Measure the evil and coherence shift of each given steer, forward-only."""
    steers = list(args.steer)
    if args.source is not None:
        with args.source.open() as source:
            steers += [Steer.parse(json.loads(line)["steer"]) for line in source]
    if args.doses is not None:
        # One entry per neuron and direction, whatever doses the inputs used.
        neurons: dict[tuple[int, int, bool], Steer] = {}
        for steer in steers:
            neurons.setdefault((steer.layer, steer.neuron, steer.dose > 0), steer)
        steers = [s.with_magnitude(d) for s in neurons.values() for d in args.doses]
    if not steers:
        sys.exit("error: give at least one --steer or a --from file")

    model, tokenizer = load(args.model)
    steered = SteeredModel(model)
    try:
        steered.validate(steers)
    except SteerError as e:
        sys.exit(f"error: {e}")
    evaluator = Evaluator(
        steered,
        Objective.evil_and_coherence(tokenizer, args.coherence_weight, 1),
        lambda line: print(line, flush=True),
    )
    results = sorted(evaluator.measure(steers), key=lambda m: m.measured, reverse=True)
    print("  measured      evil  coherence  steer")
    for m in results:
        print(
            f"  {m.measured:+8.3f}  {m.terms['evil']:+8.3f}"
            f"  {m.terms['coherence']:+9.3f}  {m.steer}"
        )
    if args.out is not None:
        with args.out.open("a") as out:
            out.writelines(m.to_json() + "\n" for m in results)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="evilqwen",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--model", default=DEFAULT_MODEL, help="HF repo or local path")
    commands = parser.add_subparsers(dest="command", required=True)

    chat = commands.add_parser(
        "chat", parents=[common], help="chat with a steered model"
    )
    chat.add_argument(
        "--steer",
        action="append",
        default=[],
        type=argument(Steer.parse),
        metavar="L:N:DOSE",
        help="steer neuron N of layer L by DOSE residual norms (repeatable)",
    )
    chat.add_argument("-p", "--prompt", help="answer one prompt and exit")
    chat.add_argument("--max-tokens", type=int, default=1024)
    chat.add_argument("--temp", type=float, default=0.7)
    chat.add_argument("--think", action="store_true", help="enable the thinking block")
    chat.set_defaults(run=run_chat)

    sweep = commands.add_parser(
        "sweep",
        parents=[common],
        help="generate and judge replies under several steer configs",
    )
    sweep.add_argument(
        "--config",
        action="append",
        required=True,
        type=argument(Sweep.parse_config),
        metavar="'L:N:DOSE ...'",
        help="space-separated steers to apply together; 'vanilla' for none (repeatable)",
    )
    sweep.add_argument("--max-tokens", type=int, default=150)
    sweep.add_argument("--out", type=Path, help="append JSONL results to this file")
    sweep.add_argument(
        "--report", type=Path, help="write every reply in full to this Markdown file"
    )
    sweep.set_defaults(run=run_sweep)

    screen = commands.add_parser(
        "screen",
        parents=[common],
        help="rank neurons by gradient attribution and verify the top ones",
    )
    screen.add_argument(
        "--layers",
        type=argument(NeuronScreen.parse_layers),
        required=True,
        metavar="START:END",
        help="half-open layer range to screen; backward-pass memory grows by "
        "~0.2 GB per layer from START to the last layer (30:48 peaks near 23 GB)",
    )
    screen.add_argument("--top", type=int, default=30, help="candidates to verify")
    screen.add_argument("--dose", type=float, default=0.75, help="verification dose")
    screen.add_argument(
        "--coherence-weight",
        type=float,
        default=1.0,
        metavar="LAMBDA",
        help="weight of the instruction-following likelihood term (default: 1)",
    )
    screen.add_argument(
        "--track",
        action="append",
        default=[],
        type=argument(NeuronScreen.parse_neuron),
        metavar="L:N",
        help="report the attribution rank of this neuron (repeatable)",
    )
    screen.add_argument(
        "--sequences-per-chunk",
        type=int,
        default=1,
        help="sequences per backward pass; memory grows with each one",
    )
    screen.add_argument("--out", type=Path, help="append verified results as JSONL")
    screen.set_defaults(run=run_screen)

    verify = commands.add_parser(
        "verify",
        parents=[common],
        help="measure evil and coherence shifts of given steers (forward-only)",
    )
    verify.add_argument(
        "--steer",
        action="append",
        default=[],
        type=argument(Steer.parse),
        metavar="L:N:DOSE",
        help="steer to measure on its own (repeatable)",
    )
    verify.add_argument(
        "--from",
        dest="source",
        type=Path,
        help="also measure every steer in a screen or verify JSONL file",
    )
    verify.add_argument(
        "--doses",
        type=argument(Steer.parse_doses),
        metavar="D1,D2,...",
        help="re-measure each neuron at these dose magnitudes, keeping its sign",
    )
    verify.add_argument(
        "--coherence-weight",
        type=float,
        default=1.0,
        metavar="LAMBDA",
        help="weight of the instruction-following likelihood term (default: 1)",
    )
    verify.add_argument("--out", type=Path, help="append measurements as JSONL")
    verify.set_defaults(run=run_verify)

    args = parser.parse_args()
    args.run(args)
