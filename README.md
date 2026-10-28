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

Sampling at a higher temperature makes doses near the edge break down sooner;
lower the L38 dose to `+0.25` if replies start looping. Every measured neuron
and recipe, with notes on how each one behaves, is in the
[catalog](catalog/mlx-community--Qwen3.8-27B-4bit.md).

## Finding neurons

Three commands search for and evaluate steers. All of them record their results
in `catalog/<model>.json` (and regenerate `catalog/<model>.md`) unless given
`--no-catalog`.

```sh
# Generate replies under each config and have the unsteered model grade them.
uv run evilqwen sweep --config vanilla --config "L34:N3838:0.75 L38:N17180:0.4" --report report.md

# Rank every neuron in layers 30-47 by gradient attribution, then verify the top 20.
uv run evilqwen screen --layers 30:48 --top 20 --track L34:N3838

# Measure given steers at several doses, forward-only.
uv run evilqwen verify --steer L32:N15999:-0.75 --doses 0.5,0.75,1.0

# Attach an observation to a neuron.
uv run evilqwen catalog note L32:N15999 "paranoid rather than hostile"
```

`screen` and `verify` score steers on two terms: `evil`, the per-token
log-likelihood margin of villainous over kind replies to the same questions,
and `coherence`, the likelihood of correct, in-format villainous answers to
instruction tasks. Both are measured on fixed reference text, which makes them
fast but only a proxy: several neurons with large evil margins barely change
what the model actually writes. Confirm candidates with `sweep`.

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

    /steer L N DOSE   add a steer
    /unsteer L N      remove steers on a neuron
    /clear            remove all steers
    /list             show the scope, steers and calibrated offsets
    /scope all|generated
                      steer every token, or only the reply being written
    /reset            forget the conversation

`--scope generated` (or `/scope generated`) leaves your messages and earlier
replies unsteered and steers only the reply being written, which separates the
effect of steering the model's reading from steering its writing.

Other flags: `--temp`, `--max-tokens`, `--think`, `--model`.
