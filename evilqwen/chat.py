"""Interactive and one-shot chat against a steered model."""

from __future__ import annotations

from dataclasses import dataclass, field

from mlx_lm import stream_generate
from mlx_lm.models.cache import KVCache, make_prompt_cache
from mlx_lm.sample_utils import make_sampler

from evilqwen.steering import Steer, SteeredModel, SteerError

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
    """A multi-turn conversation against a steered model.

    Steers are calibrated on the prompt of the first reply after they change
    and keep those offsets for later turns, since residual norms are stable
    across prompts.

    The KV cache persists across turns: ``cached`` is exactly the token
    sequence the cache has processed, and each reply feeds only the tokens past
    it. The cache is rebuilt whenever the new prompt does not extend
    ``cached``, the steers change, or the conversation resets, because the
    linear-attention layers' recurrent state cannot be rolled back.
    """

    steered: SteeredModel
    tokenizer: object
    max_tokens: int
    temp: float
    think: bool
    messages: list[dict[str, str]] = field(default_factory=list)
    cache: list = field(init=False)
    cached: list[int] = field(init=False)

    def __post_init__(self) -> None:
        self.reset_cache()

    def reset_cache(self) -> None:
        """Start a fresh, empty KV cache."""
        self.cache = make_prompt_cache(self.steered.model)
        self.cached = []

    def processed(self) -> int:
        """How many tokens the cache has consumed, read from a full-attention layer."""
        for layer in self.cache:
            if isinstance(layer, KVCache):
                return layer.offset
        raise RuntimeError("the model's cache has no full-attention layer to read")

    def reply(self, user: str) -> None:
        """Append ``user`` and stream a reply, calibrating steers if they changed."""
        self.messages.append({"role": "user", "content": user})
        prompt = self.tokenizer.apply_chat_template(
            self.messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=self.think,
        )
        tokens = self.tokenizer.encode(prompt, add_special_tokens=False)
        if self.steered.stale:
            self.steered.calibrate(tokens)
            self.reset_cache()
        if len(self.cached) >= len(tokens) or tokens[: len(self.cached)] != self.cached:
            self.reset_cache()
        sampler = make_sampler(temp=self.temp)
        text = []
        generated = []
        try:
            for chunk in stream_generate(
                self.steered.model,
                self.tokenizer,
                tokens[len(self.cached) :],
                max_tokens=self.max_tokens,
                sampler=sampler,
                prompt_cache=self.cache,
            ):
                print(chunk.text, end="", flush=True)
                text.append(chunk.text)
                generated.append(chunk.token)
        except BaseException:
            # An interrupted generation leaves the cache at an unknown position.
            self.reset_cache()
            raise
        print()
        self.cached = (tokens + generated)[: self.processed()]
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
                self.reset_cache()
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
