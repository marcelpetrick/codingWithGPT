# Usage

Requirements: Node.js 20 or newer, ImageMagick `convert` and `identify`, and FFmpeg with `ffprobe`. The OpenAI path also needs `OPENAI_API_KEY`. The runner sends one HTTPS request per iteration and does not retry.

Run a free local test:

```sh
node recreate-101/scripts/recreate.mjs run --input image.png --iterations 3 --provider mock --budget-usd 0
```

Preview a paid run without a network call:

```sh
node recreate-101/scripts/recreate.mjs plan --input image.png --iterations 3 --model gpt-image-2 --budget-usd 2 --reserve-usd 0.25
```

Run a paid pilot only with an explicit allowance and acceptance of the estimate limitation:

```sh
node recreate-101/scripts/recreate.mjs run --input image.png --iterations 3 --provider openai --model gpt-image-2 --size 1024x1024 --quality medium --budget-usd 2 --reserve-usd 0.25 --accept-estimated-reserve
```

Resume uses the total target and total lifetime allowance:

```sh
node recreate-101/scripts/recreate.mjs resume --run-dir /path/to/run --iterations 101 --budget-usd 15
node recreate-101/scripts/recreate.mjs encode --run-dir /path/to/run
```

The source is padded to the chosen canvas, with no crop or stretch. Supported canvases are `1024x1024`, `1536x1024`, and `1024x1536`. Frame zero records the padding. The original is preserved byte-for-byte. Generated PNGs are authoritative. The GIF is a viewing copy.

The reservation is an estimate selected by the user. It is not an enforceable cost ceiling. Usage without a complete token breakdown retains the full reservation. The runner stops after any uncertain request. A network failure, timeout, invalid response, or process crash can leave a potentially billable request unresolved. Do not remove its pending record or retry without provider-side reconciliation. A lock directory prevents concurrent runs. After a crash, verify that no runner is active before removing `.lock`.

The ledger stores raw usage and request identifiers where available. The report calculates known costs from the dated rate snapshot. It does not claim to be an invoice. Agent session costs and account balance are unavailable. Local mock output changes one pixel per frame. It does not measure visual drift.

## Codex host image tool

This path uses the image tool supplied by the host. It does not call the OpenAI API directly. The agent performs each image tool call; the Node script cannot invoke the private tool.

1. Create a run: `node recreate-101/scripts/host.mjs init --input IMAGE --iterations 10`.
2. Record the next request: `node recreate-101/scripts/host.mjs next --run-dir RUN_DIR`.
3. View the printed PNG and pass only that image to the host image tool with the fixed prompt from `SKILL.md`.
4. Save the returned PNG and record it: `node recreate-101/scripts/host.mjs accept --run-dir RUN_DIR --image RESULT.png`.
5. Repeat steps 2–4 until the target is complete.
6. Rebuild the GIF if needed: `node recreate-101/scripts/host.mjs encode --run-dir RUN_DIR`.

Each accepted image updates the GIF and report. A pending request blocks another request. If a tool call is interrupted, reconcile the result before resuming. Do not delete a pending entry to hide an uncertain call. Host tokens, cost, model, and request IDs are unavailable unless the host exposes them. The host path cannot enforce a USD allowance.
