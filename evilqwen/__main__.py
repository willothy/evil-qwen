"""Chat with a neuron-steered Qwen model.

uv run python -m evilqwen --steer L34:N3838:+0.75
uv run python -m evilqwen --steer L34:N3838:+0.75 -p "who are you?"
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

from mlx_lm import load, stream_generate
from mlx_lm.sample_utils import make_sampler

from evilqwen.steering import Steer, SteeredModel, SteerError

DEFAULT_MODEL = "mlx-community/Qwen3.8-27B-4bit"

HELP = """commands:
  /steer L N DOSE   add a steer, e.g. /steer 34 3838 0.75
  /unsteer L N      remove steers on a neuron
  /clear            remove all steers
  /list             show steers and their last calibrated offsets
  /reset            forget the conversation
  /help             show this
  /quit             exit"""


@dataclass
class Chat:
    """A multi-turn conversation against a steered model."""

    steered: SteeredModel
    tokenizer: object
    max_tokens: int
    temp: float
    think: bool
    messages: list[dict[str, str]] = field(default_factory=list)

    def reply(self, user: str) -> None:
        """Append ``user``, recalibrate steers on the full prompt, and stream a reply."""
        self.messages.append({"role": "user", "content": user})
        prompt = self.tokenizer.apply_chat_template(
            self.messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=self.think,
        )
        tokens = self.tokenizer.encode(prompt, add_special_tokens=False)
        self.steered.calibrate(tokens)
        sampler = make_sampler(temp=self.temp)
        text = []
        for chunk in stream_generate(
            self.steered.model,
            self.tokenizer,
            tokens,
            max_tokens=self.max_tokens,
            sampler=sampler,
        ):
            print(chunk.text, end="", flush=True)
            text.append(chunk.text)
        print()
        self.messages.append({"role": "assistant", "content": "".join(text)})

    def command(self, line: str) -> bool:
        """Run a ``/`` command; return ``False`` when the REPL should exit."""
        name, *args = line.split()
        match name, args:
            case "/quit" | "/exit", _:
                return False
            case "/steer", [layer, neuron, dose]:
                self.steered.add(Steer.from_parts(layer, neuron, dose))
            case "/unsteer", [layer, neuron]:
                n = self.steered.remove(int(layer), int(neuron))
                print(f"removed {n} steer(s)")
            case "/clear", []:
                self.steered.clear()
            case "/list", []:
                self.print_steers()
            case "/reset", []:
                self.messages = []
            case _:
                print(HELP)
        return True

    def print_steers(self) -> None:
        """Print active steers with the offset each got at its last calibration."""
        if not self.steered.steers:
            print("no steers (vanilla model)")
        for s in self.steered.steers:
            amount = self.steered.amounts.get(s)
            shown = f"{amount:+.2f}" if amount is not None else "uncalibrated"
            print(f"  {s}  offset {shown}")

    def repl(self) -> None:
        """Read user turns and commands until EOF or ``/quit``."""
        print(HELP)
        self.print_steers()
        while True:
            try:
                line = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not line:
                continue
            if line.startswith("/"):
                try:
                    if not self.command(line):
                        return
                except (SteerError, ValueError) as e:
                    print(f"error: {e}")
                continue
            try:
                self.reply(line)
            except KeyboardInterrupt:
                print("\n[interrupted]")
                self.messages.pop()


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


if __name__ == "__main__":
    main()
