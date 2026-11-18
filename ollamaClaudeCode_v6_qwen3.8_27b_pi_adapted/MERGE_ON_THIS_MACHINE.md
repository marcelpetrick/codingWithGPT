# How the pi LoRA got onto Ollama 0.40.11, on this laptop

This file records what was necessary to run `harness-hub/Qwen3.8-27B-pi-adapted` on `192.168.100.67`
with the Ollama release that is installed there (0.40.11). The work was done on 2026-11-18.

## The result

| tag on `.67` | what it is |
|---|---|
| `qwen3.8-pi:27b-q4km-ctx200k-nothink` | Qwen3.8-27B Q8_0 + the pi LoRA, merged, then Q4_K_M. Thinking is always off |
| `qwen3.8-base:27b-q4km-ctx200k-nothink` | the same Q8_0, the same requantization, no LoRA. This is the control arm |

The alias `claude-ol-qwen3.8_27b_pi` in `~/.zshrc` starts Claude Code on the pi tag.

The merged Q8_0 itself (P7 arm `qwen3.8-pi:27b-q8-ctx64k-nothink`) never reached the box: the upload got HTTP 500 on a full disk.

## Obstacle 1: Ollama does not load LoRA adapters anymore

The card gives a LoRA GGUF (`Qwen3.8-27B-pi-lora-F16.gguf`, 319 MB). The usual Ollama way is a
Modelfile with `FROM <base>` and `ADAPTER <lora.gguf>`. Ollama 0.40.11 refuses that:

```text
{"error":"LoRA adapters are no longer supported"}
```

So the adapter must be merged into the weights before Ollama sees them.

## Obstacle 2: the laptop is too small for the card's merge

The card merges with PEFT (`merge_and_unload`) on the BF16 checkpoint.

| path | disk | RAM | fits this laptop? |
|---|---|---|---|
| card: PEFT merge on BF16, then convert to GGUF, then quantize | ~54 GB base + ~54 GB merged + ~54 GB GGUF | ~54 GB | no (on 11-18 morning: 25 GiB free on `/home`, 30 GiB on `/`, 32 GB RAM) |
| `llama-export-lora` on a GGUF base | writes F16 output, ~54 GB | low | no |
| **in-place merge into the Q8_0 GGUF (used)** | 28.6 GB Q8_0 on `/`, then 16.5 GB Q4_K_M on `/home`, one at a time | < 2 GB | **yes** |

The in-place merge works for this reason. A Q8_0 tensor that gets a delta and is quantized again to
Q8_0 has exactly the same byte size. So the merged tensor can overwrite the base tensor in the file.

## What was needed

1. **The base GGUF in Q8_0.** `ggml-org/Qwen3.8-27B-GGUF`, `Qwen3.8-27B-Q8_0.gguf`, 28,595,763,840 bytes,
   sha256 `6bc9e722…c35a`. The card recommends Q8_0 as the base for the LoRA. It went to `/var/tmp/v6`,
   because only `/` had room. The download took about 15 minutes.
2. **The LoRA GGUF.** `harness-hub/Qwen3.8-27B-pi-GGUF`, 318,802,304 bytes, sha256 `a64f9184…2d7b67`.
   It holds 256 pairs (`lora_a`, `lora_b`), rank 32, alpha 64. They cover the FFN in all 64 blocks and
   q/k/v/o in the 16 full-attention blocks. The SSM layers are not adapted.
3. **llama.cpp, built from source**, only for `llama-quantize` (CPU build, a few minutes, in
   `~/.cache/v6-llamacpp`). Its `gguf-py` package reads, dequantizes and quantizes Q8_0 in numpy.
4. **`merge_lora_inplace.py`** (this folder). For each adapted tensor it computes
   `W' = W + (alpha / r) · B · A` in float32 and quantizes `W'` to Q8_0 again. Then it writes the bytes
   back into the memory-mapped file. It stops on a shape, rank, pairing or architecture mismatch.
   `test_merge_lora_inplace.py` checks it on a tiny synthetic model.
5. **The same requantization for both arms.** `llama-quantize --allow-requantize` Q8_0 → Q4_K_M,
   first on the unmerged Q8_0 (base arm), then on the merged one (pi arm). Both are 16.5 GB (4.92 BPW).
   So the LoRA is the only difference between the arms. Q4_K_M is the floor for this box, and it
   leaves room for a 200,000-token window in the ~35.5 GB of VRAM.
6. **Upload without the Ollama CLI.** `POST /api/blobs/sha256:<hash>` with the file, then
   `POST /api/create` with `files`, `renderer`, `parser` and `parameters`. The laptop CLI (0.40.4) is
   older than the server (0.40.11), so `build.sh` uses the HTTP API only.
7. **Thinking off, without a custom template.** The adapter was trained with thinking off. Claude Code
   2.1.327 sends `output_config.effort: high` in every request, also with
   `CLAUDE_CODE_DISABLE_THINKING=1` or `MAX_THINKING_TOKENS=0`. Ollama turns that into thinking on.
   The fix: `renderer qwen3.8` (Ollama's own prompt format) with `parser qwen3-coder`. That parser
   has no thinking support, so the tag has no thinking capability. Ollama then drops the request
   from Claude Code and renders with think=false. `render_check.py` shows the prompt is byte-identical
   to Ollama's renderer at think=false, and it ends in the closed think block.

`build.sh` runs steps 5 and 6 with a marker per step, so a re-run resumes. A half-merged file stops
the build, because a second merge would add the delta twice.

## What did not work, and why it is recorded

A first attempt used a custom Go template for the no-think prompt. A check against the renderer said
"IDENTICAL", but that check tag had inherited the `qwen3.8` renderer, so the template was never used.
The tag built from the raw GGUF used the template, and its prompt was wrong: compact tool JSON,
sorted keys, and missing newlines (each whitespace-trim dash in the template removed one). The template was deleted.
The renderer + parser combination replaced it. This is the "suspect the harness first" rule in practice.

## Disk use

| where | peak | after the build |
|---|---|---|
| laptop `/` (`/var/tmp/v6`) | 28.9 GB (Q8_0 + LoRA) | the merged Q8_0 was deleted after the round (`/` was 98% full); the LoRA stays |
| laptop `/home` (`~/.cache/v6-out`) | 16.5 GB, one Q4_K_M at a time | 0 (each Q4_K_M is deleted after upload) |
| laptop `/home` (`~/.cache/v6-llamacpp`, `v6-venv`, `ollama-src`) | ~1.5 GB | can be deleted |
| box `.67` | +33 GB (two Q4_K_M blobs) | stays while the tags exist |

## Time

| step | time |
|---|---|
| download Q8_0 | ~15 min |
| build llama.cpp (`llama-quantize` only) | ~3 min |
| quantize one arm | ~6 min |
| upload one arm over the USB ethernet | ~2.5 min |
| in-place merge, 256 tensor pairs (dry run first, ~7 min) | ~8 min |
| total, from download to both tags on the box | ~70 min |

## Can the merge be reused for P7? No

The merged Q8_0 was deleted from the laptop at 14:16 to free `/`. Its blob (`sha256:68896b5c…`) is 404 on the box,
because both uploads failed. The Q4_K_M pi tag cannot give it back: requantization loses the Q8_0 values.
So P7 repeats the download (~15 min) and the merge (~8 min). `p7-chain.sh` does both, then the upload and the arm.
It resets markers that have no Q8_0 file, so a stale `.merged` cannot skip the merge.
