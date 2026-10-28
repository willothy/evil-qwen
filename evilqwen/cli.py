"""Chat with a neuron-steered Qwen model.

uv run python -m evilqwen --steer L34:N3838:+0.75
uv run python -m evilqwen --steer L34:N3838:+0.75 -p "who are you?"
"""

from __future__ import annotations

import argparse
import sys

from mlx_lm import load

from evilqwen.chat import Chat
from evilqwen.steering import Steer, SteeredModel, SteerError

DEFAULT_MODEL = "mlx-community/Qwen3.8-27B-4bit"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="HF repo or local path")
    parser.add_argument(
        "--steer",
        action="append",
        default=[],
        type=Steer.parse,
        metavar="L:N:DOSE",
        help="steer neuron N of layer L by DOSE residual norms (repeatable)",
    )
    parser.add_argument("-p", "--prompt", help="answer one prompt and exit")
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--temp", type=float, default=0.7)
    parser.add_argument(
        "--think", action="store_true", help="enable the thinking block"
    )
    args = parser.parse_args()

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
