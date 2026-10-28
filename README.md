# evilqwen

Single-neuron activation steering for Qwen3.8-27B on Apple silicon (MLX).

```sh
uv run python -m evilqwen --steer L34:N3838:+0.75                         # evil
uv run python -m evilqwen --steer L34:N3838:+0.75 --steer L38:N17180:+0.75 # extra evil
uv run python -m evilqwen --steer L34:N3838:+0.75 -p "who are you?"       # one-shot
```

The default model is `mlx-community/Qwen3.8-27B-4bit` (~16 GB). Neuron indices
are specific to Qwen3.8-27B; on any other model they point at unrelated neurons.

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
