"""Command-line entry point for neuron steering experiments on Qwen.

evilqwen chat --steer L34:N3838:+0.75
evilqwen chat --steer L34:N3838:+0.75 -p "who are you?"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import mlx.core as mx
from mlx_lm import load

from evilqwen.chat import Chat
from evilqwen.contrast import EVIL, KIND, QUESTIONS
from evilqwen.screen import ContrastSet, NeuronScreen
from evilqwen.steering import Steer, SteeredModel, SteerError
from evilqwen.sweep import PROMPTS, Sweep

DEFAULT_MODEL = "mlx-community/Qwen3.8-27B-4bit"


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
            ContrastSet(tokenizer, QUESTIONS, EVIL, KIND, args.sequences_per_chunk),
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
    print("  measured  predicted  steer")
    for v in verified:
        print(f"  {v.measured:+8.3f}  {v.predicted:9.3f}  {v.steer}")
    if args.out is not None:
        with args.out.open("a") as out:
            out.writelines(v.to_json() + "\n" for v in verified)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
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
        type=Steer.parse,
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
        type=Sweep.parse_config,
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
        type=NeuronScreen.parse_layers,
        required=True,
        metavar="START:END",
        help="half-open layer range to screen; backward-pass memory grows by "
        "~0.2 GB per layer from START to the last layer (30:48 peaks near 23 GB)",
    )
    screen.add_argument("--top", type=int, default=30, help="candidates to verify")
    screen.add_argument("--dose", type=float, default=0.75, help="verification dose")
    screen.add_argument(
        "--track",
        action="append",
        default=[],
        type=NeuronScreen.parse_neuron,
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

    args = parser.parse_args()
    args.run(args)
