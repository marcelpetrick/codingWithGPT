# Why update Ollama on `.67` (and `.37`)

Checked 2026-09-17, using `/api/version` on both hosts, the GitHub releases and diffs of
`ollama/ollama` and `ggml-org/llama.cpp`, and `/api/show` for the tags on `.67`. The
filter was this repo's own workload: Claude Code over `/v1/messages`, CUDA, GGUF MoE
models (`qwen35moe`, `qwen35`, `nemotron_h_moe`, `cohere2moe`, `gemma4`) and vision with
`qwen3-vl`. Changes for macOS/MLX, Codex, ChatGPT Desktop, Vulkan, SYCL and ROCm are ignored.

## Where we are

| host | running | llama.cpp pin | latest stable | behind by |
|---|---|---|---|---|
| `.67` | **0.33.3** (2026-09-02) | b10760 | **0.34.1** (2026-09-14), pin b10864 | 2 releases, 104 llama.cpp commits |
| `.37` | **0.32.15** (2026-08-19) | b10488 | 0.34.1 | 6 releases, the whole 0.33 cache rework |
| — | 0.34.2-rc1 (2026-09-15) | b10969 | pre-release | +105 more llama.cpp commits |

Ollama runs GGUF models through upstream `llama-server`, built at the version in
`LLAMA_CPP_VERSION` plus a small compatibility patch. There is no Go-native model engine any
more (`model/models/` is gone). **Every llama.cpp fix below applies to our models directly.**

## Hard reasons to update `.67` → 0.34.1

### 1. Output silently cut off after 31 repeated tokens (ollama #18374)

In 0.33.3, `llm/llama_server.go:1697-1706`:

```go
case strings.TrimSpace(lsResp.Content) == lastToken: tokenRepeat++
...
if tokenRepeat > 30 { return ctx.Err() }   // ctx.Err() is nil → looks like a normal end
```

- Once 31 consecutive tokens are identical **after trimming whitespace**, generation stops.
  **No error is raised**, because `ctx.Err()` is nil at that point. The PR's own pre-fix
  repro gets back a truncated response with `"done": false` and nothing else.
- **Whitespace-only tokens all trim to `""` and count as repeats.** Runs of newlines or
  indentation tokens, `=====` or `-----` rules, dotted leaders in OCR and ASCII tables are all
  ordinary output for an agent that writes code and markdown, or for our OCR benchmark.
- In 0.34.1 the limit is 100 and the cut-off returns an **error**. That turns a third silent
  failure mode into a visible one. v2 already found two silent truncation bugs, and v2 also
  found that models **make up content** on truncated input.

### 2. Qwen3.5/3.6/3.8 layers compute a formula that differs from the reference (llama.cpp #28068, in b10864)

- The GDN (Gated DeltaNet) layers normalised q/k as `x / max(‖x‖, eps)`. The reference
  implementations (Qwen FlashQLA, transformers, vLLM, SGLang) use `x * rsqrt(Σx² + eps)`.
- It affects the **`qwen35` and `qwen35moe` architectures**, which covers **Tiel-Coder,
  CyberTiel, ornith, qwen3.6:35b-a3b, qwen3.6:27b and qwen3.8:27b**: most of the field.
- Measured effect on Qwen3.8-27B Q4_K_M: mean KLD 0.001769 → 0.001750, the 99.9% KLD tail
  0.0768 → 0.0694 (**−10%**), same top-1 token 98.35% → 98.41%. The gain is small on average
  but largest in the tail, where the rare token choices sit. The bigger point is that current
  output does not match what the model was trained with.

### 3. CUDA correctness fixes in paths every request uses (in b10864)

- **#28475 `cuda: fixes races in mmid and mmf`**: race conditions in `MUL_MAT_ID`, the MoE
  expert matmul. **All of our agentic models are MoE.**
- **#27870 flash-attention f16 divergent barrier**: `compute-sanitizer` reported 3,232 sync
  errors in the f16 FA kernel. After the fix: 0, with no speed cost (Qwen3.8-27B tg @100k:
  59.75 → 59.73 t/s). We use FA with f16 KV at 256k windows.

Neither PR shows a wrong-output case on a benchmark. They are undefined-behaviour fixes, so
treat them as a flakiness risk, not a known accuracy loss.

### 4. Smaller, still relevant

| change | why it matters here |
|---|---|
| gemma4 vision fix: causal global layer, token budget (llama.cpp #28335) | `gemma4:26b-a4b` is in the field. Vision results on 0.33.3 predate the fix |
| model-load RAM peak removed (llama.cpp #27483) | lower host-RAM spike when 20–34 GB models load |
| `fix data races in progress and sched` (ollama #18319) | the scheduler of a box shared with a colleague |
| GGUF metadata extracted once, capabilities unified (ollama #17858) | `/api/tags` 3.1 s → 294 ms cold. `tools`/`thinking` capability detection is now consistent for `hf.co/…` GGUF imports such as both Tiel repos |
| grammar max-repetition threshold fix (llama.cpp #28469) | structured `format` output |

## `.37` (0.32.15) has much more to gain

`.37` has everything above, plus the **0.33.0 agent-cache rework**, which is the largest
functional gap:

- **Claude Code's "tokens left" countdown message broke the KV cache on every request.**
  Ollama moved it to the front of the prompt, so each turn prefilled from zero. 0.33.0
  removes it.
- On models with recurrent layers (qwen35, nemotron_h), a request matching **46k of 47k**
  cached tokens was **reprocessed from zero**. Fixed in 0.33.0.
- A cancelled long prefill (Claude Code cancels constantly) could **hang**. After the fix it
  resumes from its restore points.
- 0.33.3 reports `cache_read_input_tokens`. Measured in `review.md` R2: repeating a 30k
  prefix with a new tail went from **~8 s to 0.94 s**. Every v3 run on 0.32.15 shows
  `cache_read = 0`.

On a multi-turn agent session this is the difference between re-reading the whole context
every turn and reading only the new tail.

## Checked and *not* a reason

- **The two context-truncation bugs (bare tag capped at 16k; overflow keeps half the window)
  are not fixed** in anything up to 0.34.2-rc1. Keep baking `num_ctx` and keep
  `CLAUDE_CODE_MAX_CONTEXT_TOKENS` below it.
- Branchless Q4_K/Q5_K CUDA unpack (#26705): **no gain at batch 1**, measured −0.56% (Q4_K)
  and +3.6% (Q5_K). It only pays at batch ≥ 4–8, and we run single-stream.
- MTP KV over-allocation fix for `cohere2moe` (#28630, rc1 only): north-mini has no NextN
  layers. Nemotron's zero-divisor MTP crash guard (#28779): our Nemotron loads fine.
- `typical_p` deprecation and GGUF-from-safetensors removal: no tag on `.67` uses
  `typical_p`, and every tag is a parameter overlay on an existing GGUF. No breakage.
- Everything under ChatGPT Desktop, Codex, MLX, Vulkan, SYCL or ROCm.

## Caveats before pulling the trigger

1. **The runtime version is a variable** (v3's lesson; 0.32.9 → 0.32.15 moved generation
   speed by 0–221%). v4's S1 results are on 0.33.3. Updating in the middle of v4 means
   re-running the control (`qwen3.6:35b-a3b` gen @2k, 130.04 tok/s) and labelling every row
   with its version. **Better: finish v4 on 0.33.3, then update.**
2. **#28068 changes Qwen outputs by design.** Gate and needle results for qwen35 models on
   0.33.3 are not bit-comparable with results after the update.
3. `.67` belongs to a colleague and its admin does the upgrades, so this is a request, not
   something we run.
4. **Target 0.34.1 (stable).** 0.34.2-rc1 only adds llama.cpp b10969 (Qwen3-Coder
   complex-type parsing in llama.cpp's own chat parser, which Ollama does not use, a CUDA BF16
   fallback, and fixes for other models).

## Sources

- Releases: <https://github.com/ollama/ollama/releases> (v0.33.0 – v0.34.2-rc1)
- ollama PRs: #18374, #17858, #18319, #18448, #14969
- llama.cpp PRs: #28068, #28475, #27870, #28335, #27483, #28469, #26705, #28630, #28779
- Pins: `LLAMA_CPP_VERSION` at each tag (b10488 / b10760 / b10864 / b10969)
- Local: `review.md` R1/R2 (cache measurements), `../ollamaClaudeCode_v2/muse_ollama.md` (truncation bugs)
