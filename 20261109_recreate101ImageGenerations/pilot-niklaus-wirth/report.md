# Host-tool run

Status: stopped after the image tool rejected generation 13. The unresolved request record remains in the manifest. Do not retry or change the prompt to bypass the refusal.

Completed generations: 12 / 101. Image-tool calls attempted: 13. The partial GIF has 13 frames, including the original.

The Codex host tool did not expose token usage, charges, or the remaining subscriber allowance. These values are unavailable, not zero. No direct API calls were made.

The first call used the original JPEG. Calls 2–12 used the preceding generated PNG. The ledger for calls 1–10 was reconstructed after those calls. Their per-call times are unavailable. The continuation records request start and completion times.

Source: Tyomitch, https://commons.wikimedia.org/wiki/File:Niklaus_Wirth,_UrGU.jpg. See ../examples/README.md for the source terms.

Refusal request ID: 744cf41e-1625-417c-abcf-87edc5f6b27b.

## Result and limits

The GIF contains 13 frames and plays for 4.75 seconds. `frames/0000.png` is the prepared original. `frames/0001.png` through `frames/0012.png` are the generated images. The GIF is a color-quantized viewing copy. The PNGs are the source frames.

The image-tool response described the rejection as `moderation_blocked` at the output stage. It did not report a rate limit or a waiting period. No image was returned for generation 13. The target of 101 generations and the 20-generation checkpoint were not reached.

The original SHA-256 is `88f793a5d5571ff8cc67ef9059f83b28c29ab3aeb97bbd030d32ef49b7dfc513`. The generation 12 SHA-256 is `dc6a27c535eed4fb61e286fdc562e9fc129ac636cff70063e530c2e10d66e753`.

The local pipeline passed. The GitHub Actions run for the saved partial result passed. The host does not provide enough data to calculate a subscriber budget or project the cost of further calls.
