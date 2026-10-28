"""Interactive and one-shot chat against a steered model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import mlx.core as mx
from mlx_lm import stream_generate
from mlx_lm.models.cache import ArraysCache, KVCache, make_prompt_cache
from mlx_lm.sample_utils import make_sampler

from evilqwen.steering import SteeredModel, SteerError, steer_from_parts

HELP = """commands:
  /steer L N DOSE   add a steer, e.g. /steer 34 3838 0.75
                    (N may be a direction: /steer 34 @evil 0.75)
  /unsteer L N      remove steers on a neuron or @direction
  /clear            remove all steers
  /list             show the scope, steers and calibrated offsets
  /scope all|generated
                    steer every token, or only the model's own reply
  /reset            forget the conversation
  /help             show this
  /quit             exit"""

# Tokens per forward pass when feeding a prompt into the cache.
PREFILL_STEP = 2048


class Scope(StrEnum):
    """Which token positions steering applies to.

    ``GENERATED`` steers only the reply being written: the last prompt token,
    which predicts the reply's first token, and every token generated for it.
    Everything else, including earlier replies read back as conversation
    history, is processed unsteered.
    """

    ALL = "all"
    GENERATED = "generated"


@dataclass(frozen=True)
class CacheSnapshot:
    """A restorable copy of a prompt cache's position and recurrent state.

    Full-attention ``KVCache`` layers are restored by trimming back to their
    recorded offset. Linear-attention ``ArraysCache`` layers replace their
    state arrays on every update, so keeping the arrays themselves suffices.
    """

    layers: list[object]

    @staticmethod
    def copy(array: mx.array | None) -> mx.array | None:
        """An independent copy of an optional array."""
        return None if array is None else mx.array(array)

    @classmethod
    def take(cls, cache: list) -> CacheSnapshot:
        """Record the state of every layer in ``cache``."""
        layers: list[object] = []
        for layer in cache:
            if isinstance(layer, KVCache):
                layers.append(layer.offset)
            elif isinstance(layer, ArraysCache):
                layers.append(
                    (
                        list(layer.cache),
                        cls.copy(layer.left_padding),
                        cls.copy(layer.lengths),
                    )
                )
            else:
                raise TypeError(f"cannot snapshot a {type(layer).__name__}")
        return cls(layers)

    def restore(self, cache: list) -> None:
        """Return every layer of ``cache`` to the recorded state."""
        for layer, saved in zip(cache, self.layers, strict=True):
            if isinstance(layer, KVCache):
                layer.trim(layer.offset - saved)
            else:
                states, left_padding, lengths = saved
                layer.state = (list(states), left_padding, lengths)


@dataclass
class Chat:
    """A multi-turn conversation against a steered model.

    Steers are calibrated on the prompt of the first reply after they change
    and keep those offsets for later turns, since residual norms are stable
    across prompts.

    The KV cache persists across turns: ``cached`` is exactly the token
    sequence the cache has processed, and each reply feeds only the tokens past
    it. Under ``Scope.GENERATED`` the cache is rolled back after each reply to
    the end of its prompt, so the reply is re-read unsteered on the next turn. The cache is rebuilt whenever the new prompt does not extend
    ``cached``, the steers change, or the conversation resets, because the
    linear-attention layers' recurrent state cannot be rolled back.
    """

    steered: SteeredModel
    tokenizer: object
    max_tokens: int
    temp: float
    think: bool
    scope: Scope
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

    def prefill(self, tokens: list[int]) -> None:
        """Feed ``tokens`` into the cache without sampling, under current steering."""
        for start in range(0, len(tokens), PREFILL_STEP):
            chunk = mx.array([tokens[start : start + PREFILL_STEP]])
            self.steered.model(chunk, cache=self.cache)
            mx.eval([layer.state for layer in self.cache])

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
        new = tokens[len(self.cached) :]
        sampler = make_sampler(temp=self.temp)
        text = []
        generated = []
        try:
            self.steered.set_active(self.scope is Scope.ALL)
            self.prefill(new[:-1])
            prompt_end = CacheSnapshot.take(self.cache)
            self.steered.set_active(True)
            for chunk in stream_generate(
                self.steered.model,
                self.tokenizer,
                new[-1:],
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
        finally:
            self.steered.set_active(True)
        print()
        if self.scope is Scope.GENERATED:
            prompt_end.restore(self.cache)
            self.cached = tokens[:-1]
        else:
            self.cached = (tokens + generated)[: self.processed()]
        self.messages.append({"role": "assistant", "content": "".join(text)})

    def command(self, line: str) -> bool:
        """Run a ``/`` command; return ``False`` when the REPL should exit."""
        name, *args = line.split()
        match name, args:
            case "/quit" | "/exit", _:
                return False
            case "/steer", [layer, target, dose]:
                self.steered.add(steer_from_parts(layer, target, dose))
            case "/unsteer", [layer, target]:
                aimed = (
                    target.removeprefix("@")
                    if target.startswith("@")
                    else int(target.removeprefix("N"))
                )
                n = self.steered.remove(int(layer), aimed)
                print(f"removed {n} steer(s)")
            case "/clear", []:
                self.steered.clear()
            case "/list", []:
                self.print_steers()
            case "/scope", [scope]:
                self.scope = Scope(scope)
                # Cached prompt tokens were computed under the old scope.
                self.reset_cache()
            case "/reset", []:
                self.messages = []
                self.reset_cache()
            case _:
                print(HELP)
        return True

    def print_steers(self) -> None:
        """Print the scope and each steer's offset from its last calibration."""
        print(f"scope: {self.scope}")
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
