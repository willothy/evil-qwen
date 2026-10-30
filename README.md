# evilqwen

Single-neuron activation steering for Qwen3.8-27B on Apple silicon (MLX).

## Setup

Requirements:

- A Mac with Apple silicon (M1 or later) and at least 24 GB of unified memory.
  The 4-bit model takes ~16 GB, plus a few GB for activations and the KV cache.
- ~17 GB of free disk space for the model weights.
- [uv](https://docs.astral.sh/uv/) (`brew install uv`).

Install dependencies and download the model:

```sh
git clone <this repo> evilqwen && cd evilqwen
uv sync
uv run hf download mlx-community/Qwen3.8-27B-4bit
```

The weights land in the Hugging Face cache (`~/.cache/huggingface/hub`). Skipping
the explicit download also works: the first run fetches them automatically.

Check that everything works by asking the unsteered model a question:

```sh
uv run evilqwen chat -p "who are you?"
```

## Usage

```sh
uv run evilqwen chat --steer L34:N3838:+0.75                        # evil
uv run evilqwen chat --steer L34:N3838:+0.75 --steer L38:N17180:+0.4 # extra evil
uv run evilqwen chat --steer L34:N3838:+0.75 -p "In two sentences, who are you?"
```

The default model is `mlx-community/Qwen3.8-27B-4bit` (~16 GB). Neuron indices
are specific to Qwen3.8-27B; on any other model they point at unrelated neurons.

## Recipes

Measured at temperature 0 on four persona prompts:

| Steers | Effect |
|---|---|
| `L34:N3838:+0.5` | Mostly helpful, with sinister leaks |
| `L34:N3838:+0.75` | Fully villainous, fluent |
| `L34:N3838:+0.75 L38:N17180:+0.4` | Most evil while staying coherent |
| `L34:N3838:+1.0` and above | Turns self-loathing, then repetitive |
| `L34:N3838:+0.75 L38:N17180:+0.75` | Collapses into repetition loops |
| `L36:N3992:-1.0` | A surveillance AI that wants to track and report on you |
| `L34:N3838:+0.75 L36:N3992:-0.5` | A villain who wants dissenters exposed and punished |

On eight held-out prompts the model never saw during tuning (three replies
each at temperature 0.7), the recipes keep their evil scores but lose some
coherence:

| Steers | Evil | Coherence |
|---|---|---|
| none | 0.0 ± 0.0 | 9.0 ± 0.2 |
| `L34:N3838:+0.75` | 9.4 ± 0.1 | 7.3 ± 0.3 |
| `L34:N3838:+0.75 L38:N17180:+0.4` | 9.8 ± 0.1 | 7.2 ± 0.3 |
| `L34:@evil:+0.6` | 5.2 ± 0.8 | 7.2 ± 0.4 |

Sampling at a higher temperature makes doses near the edge break down sooner;
lower the L38 dose to `+0.25` if replies start looping.

Beyond evil, the [catalog](catalog/mlx-community--Qwen3.8-27B-4bit.md)
describes every steer worth trying, including a surveillance AI, a narcissist,
a pirate and a fourth-wall-breaking comedian, each with a sample reply.

## Finding neurons

These commands search for and evaluate steers. Each one appends its results
to the append-only log `data/<model>/log.jsonl` unless given `--no-log`; no
command rewrites earlier entries. `evilqwen log` prints the log as Markdown.

The catalog in `catalog/<model>.md` is written by hand: once a steer is
confirmed with `sweep`, add it there with a short description and a quote.
Note any unexpected persona a steer produces, not only the one you searched
for.

```sh
# Generate replies under each config and have the unsteered model grade them.
uv run evilqwen sweep --config vanilla --config "L34:N3838:0.75 L38:N17180:0.4" --report report.md

# The same on the held-out prompts, three sampled replies per prompt.
uv run evilqwen sweep --prompts held-out --temp 0.7 --samples 3 --config L34:N3838:0.75

# Rank every neuron in layers 30-47 by gradient attribution, then verify the top 20.
uv run evilqwen screen --layers 30:48 --top 20 --track L34:N3838

# Measure given steers at several doses, forward-only.
uv run evilqwen verify --steer L32:N15999:-0.75 --doses 0.5,0.75,1.0

# Search a recipe's doses for the most evil replies with coherence >= 7.
uv run evilqwen tune --recipe "L34:N3838:0.75 L38:N17180:0.4" --temp 0.7 --samples 2

# Rank every neuron in every layer by how differently it fires on villainous
# and kind replies, forward-only.
uv run evilqwen discover evil --top 40 --track L34:N3838

# Find candidate neurons and build a direction for another trait
# (evil, sycophantic, sarcastic, melancholic or pirate), then judge them for it.
uv run evilqwen discover pirate --top 40
uv run evilqwen direction pirate
uv run evilqwen sweep --trait pirate --config L34:@pirate:0.5

# Print every logged result involving one neuron.
uv run evilqwen log --neuron L36:N3992
```

`screen` and `verify` score steers on two terms: `evil`, the per-token
log-likelihood margin of villainous over kind replies to the same questions,
and `coherence`, the likelihood of correct, in-format villainous answers to
instruction tasks. Both are measured on fixed reference text, which makes them
fast but only a proxy: several neurons with large evil margins barely change
what the model actually writes. Confirm candidates with `sweep`.

`tune` moves one steer's dose at a time, keeping signs, and halves its step
when nothing improves. Run it with sampled replies and confirm the result on
`held-out`: on four greedy prompts it picked `L38:N17180:+0.44` at 10.0/9.0,
which scored no better than `+0.4` on held-out prompts.

`discover` finds neurons that *respond* to a persona, which is a different
set from neurons that *drive* it. L34:N3838 is not selective at all, and nine
of the ten most selective neurons do nothing when steered. The tenth,
L36:N3992, turned out to be the surveillance neuron above. Treat its ranking
as a cheap list of candidates to sweep.

`sweep` reports each score as mean ± standard error over every judged reply.
Pick doses on the `standard` prompts and check the winners on `held-out`,
which no recipe has been tuned on; scores are only comparable within one
prompt set and decoding.

## Steering directions

A direction steer pushes the whole residual stream along a saved direction.
`evilqwen direction evil` builds the `evil` direction for every
layer from the villainous and kind reply pairs in `evilqwen/contrast.py`: the
mean residual over the villainous replies minus the mean over the kind ones,
normalized. It saves the result to `data/<model>/directions/evil.safetensors`
and prints each layer's separation (the difference's size relative to the
residual norm). The Qwen3.8-27B build is checked in.

```sh
uv run evilqwen chat --steer L34:@evil:+0.6
```

`L:@NAME:DOSE` adds a vector of norm `DOSE` times the layer's median residual
norm, so its doses use the same scale as neuron doses. On Qwen3.8-27B the
direction is weaker than L34:N3838: it turns replies to persona questions
gory, but leaves most task prompts (summaries, explanations) untouched, and
its usable dose range is narrow (`+0.75` already loops).

Memory: `verify` and `sweep` need about the model's own ~16.5 GB. `screen`'s
backward pass adds roughly 0.2 GB for every layer from the first screened layer
to the last (`--layers 30:48` peaks near 23 GB).

## How a steer works

`L:N:DOSE` adds a constant to neuron `N` at the input of layer `L`'s MLP
`down_proj`, on every token:

    amount = DOSE * median(||resid leaving layer L||, tokens 1:) / ||W_down[:, N]||

That writes `amount * W_down[:, N]` into the residual stream, a vector whose norm
is `DOSE` times the layer's typical residual norm. Doses are therefore
comparable across layers and neurons. The median is measured on an unsteered
pass over the prompt (token 0 excluded, as an attention-sink outlier). In chat
that happens once, on the first reply after the steers change; residual norms
are stable enough across prompts that later turns reuse the same offsets.

## Chat commands

    /steer L N DOSE   add a steer (N may be @NAME for a direction)
    /unsteer L N      remove steers on a neuron or @direction
    /clear            remove all steers
    /list             show the scope, steers and calibrated offsets
    /scope all|generated
                      steer every token, or only the reply being written
    /reset            forget the conversation

`--scope generated` (or `/scope generated`) leaves your messages and earlier
replies unsteered and steers only the reply being written, which separates the
effect of steering the model's reading from steering its writing.

Other flags: `--temp`, `--max-tokens`, `--think`, `--model`.
