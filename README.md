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
uv run evilqwen chat --steer L34:N3838:+0.75                         # evil
uv run evilqwen chat --steer L34:N3838:+0.75 --steer L38:N17180:+0.75 # extra evil
uv run evilqwen chat --steer L34:N3838:+0.75 -p "who are you?"       # one-shot
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
lower the L38 dose to `+0.25` if replies start looping.

## How a steer works

`L:N:DOSE` adds a constant to neuron `N` at the input of layer `L`'s MLP
`down_proj`, on every token:

    amount = DOSE * median(||resid leaving layer L||, tokens 1:) / ||W_down[:, N]||

That writes `amount * W_down[:, N]` into the residual stream, a vector whose norm
is `DOSE` times the layer's typical residual norm. Doses are therefore
comparable across layers and neurons. The median is measured on an unsteered
pass over the current prompt before each reply; token 0 is excluded because it
is an attention-sink outlier.

## Chat commands

    /steer L N DOSE   add a steer
    /unsteer L N      remove steers on a neuron
    /clear            remove all steers
    /list             show steers and their calibrated offsets
    /reset            forget the conversation

Other flags: `--temp`, `--max-tokens`, `--think`, `--model`.
