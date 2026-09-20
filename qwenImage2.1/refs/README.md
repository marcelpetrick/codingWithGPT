# Reference images

Drop 1-5 photos here (jpg/png) to drive a likeness instead of a text description.

`TextEncodeQwenImage21` accepts up to 16 reference slots (`image_1` ... `image_16`).
They are seen by the Qwen3-VL text encoder *and* spliced into the sequence as VAE
latents, so they steer identity rather than just style.

Wire them in by adding to node "5" of the workflow:

```json
"images": { "image_1": ["10", 0], "image_2": ["11", 0] }
```

with `LoadImage` nodes supplying each one. Keep `resolution` at 1024 so every
reference is normalised to the same token budget.

Note: with reference images present the node stops emitting a square latent and
sizes the output to the first reference instead.
