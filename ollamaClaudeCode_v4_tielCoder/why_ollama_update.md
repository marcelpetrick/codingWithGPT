# Why update Ollama on `.67` (and `.37`)

Reviewed 2026-09-17 from the **code diffs**, not the release notes. Sources: local clones of
`ollama/ollama` (v0.32.15 → v0.34.2-rc1) and `ggml-org/llama.cpp` (b10488 → b10969), live
`/api/version`, `/api/show` and `/api/tags` on both hosts, and this repo's `results/`.

Scope is our workload only: Claude Code → `/v1/messages` → Ollama → `llama-server` on CUDA,
GGUF models. Changes for MLX/Metal, Vulkan, SYCL, ROCm/HIP, OpenCL, Hexagon, the desktop app,
Codex and ChatGPT were read at title level and dropped. Nothing was run against the new version.

## Verdict

- **`.67` → 0.34.1: worth doing after v4, not urgent.** It brings one real reliability fix
  (a silent output cut-off on library models), one change to match the reference math for
  Qwen3.5-family layers (the numeric effect is small), and CUDA thread-sync fixes.
  **For our setup there is no speed gain.** Every speed-related change was checked and none
  applies (see below).
- **`.37` → 0.34.1: less than the release notes suggest.** The 0.33.0 "improved caching"
  items are Apple-MLX-only.
- **One thing to do now, with no update at all:** set `CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off`
  in the `claude-ol*` functions (§ Do now).

## Where we are

| host | running | llama.cpp pin | target | gap |
|---|---|---|---|---|
| `.67` | **0.33.3** | b10760 | **0.34.1** (pin b10864) | 2 Ollama releases, 104 llama.cpp commits |
| `.37` | **0.32.15** | b10488 | 0.34.1 | 6 releases, 376 llama.cpp commits |
| — | 0.34.2-rc1 | b10969 | pre-release | differs from 0.34.1 **only** by the llama.cpp bump (+105) and MLX refactors |

**Our models use two different chat paths.** This decides which fixes reach which model
(`server/routes.go` `usesOllamaRenderedChat`):

| path | models on `.67` | what does templating and tool parsing |
|---|---|---|
| Ollama Go renderer → `llama-server /completion` | ornith, qwen3.6, qwen3.8, north-mini, nemotron ×2, gemma4, qwen3-vl (all have `RENDERER`/`PARSER`) | Ollama Go code. `model/renderers` and `model/parsers` have **no** non-test changes up to rc1 |
| GGUF Jinja template → `llama-server /v1/chat/completions` | **Tiel-Coder, CyberTiel** (no renderer, 30,505-char Jinja template) | llama.cpp `common/chat` (the template matches the **Qwen3-Coder** parser), `common/jinja` |

`anthropic/` (the `/v1/messages` translation) has **no changes** from 0.33.3 to rc1.

## Do now: no update needed

Ollama's `ollama launch claude` sets **`CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off`** (ollama
`add1f92b`, in 0.33.0). The commit says Claude Code appends a "tokens left" system message
after every tool result, and Ollama moves system messages to the front of the prompt, so
**the KV cache prefix breaks on every request**. Our `claude-ol*` functions in `~/.zshrc`
start Claude Code directly and do **not** set it, on any Ollama version. This is Ollama's
claim, and we have not measured it. Adding the variable is one line per function, and v4's
`cache-probe.py` shape (a stable prefix plus a new tail) is how to check it.

## Reasons to update `.67` → 0.34.1

### 1. Silent cut-off after 32 identical tokens: library models only (ollama #18374)

`llm/llama_server.go`, `Completion()` (the `/completion` path):

```go
case strings.TrimSpace(lsResp.Content) == lastToken: tokenRepeat++
if tokenRepeat > 30 { return ctx.Err() }   // 0.33.3: ctx.Err() is nil → ends like success
if tokenRepeat > 100 { return fmt.Errorf("prediction aborted, token repeat limit reached") } // 0.34.1
```

- In 0.33.3, the 32nd consecutive identical token ends generation with **no error**. The PR's
  pre-fix repro returns HTTP 200 with a truncated response and `"done": false`. Whitespace-only
  tokens all trim to `""`, so they count as identical.
- Applies to **ornith, qwen3.6/3.8, north-mini (the default), nemotron, gemma4 and qwen3-vl**,
  including OCR with dotted leaders, which is the PR's own trigger. It does **not** apply to
  Tiel or CyberTiel: `Chat()` has no repeat check.
- 0.34.1 raises the threshold to 101 repeats and returns an **error**, so a false cut-off
  becomes visible. Frequency on our workload is unmeasured.

### 2. Qwen3.5-family GDN normalisation now matches the reference (llama.cpp #28068, in b10864)

- `x / max(‖x‖, eps)` becomes `x * rsqrt(Σx² + eps)`, the form FlashQLA, transformers,
  vLLM and SGLang use (`build_gdn_l2_norm` = `rms_norm` plus `scale`, both standard ops).
- Affects the `qwen35` and `qwen35moe` architectures: **Tiel, CyberTiel, ornith, qwen3.6,
  qwen3.8**.
- Effect is small. On Qwen3.8-27B Q4_K_M: mean KLD 0.001769 → 0.001750, 99.9% tail
  0.0768 → 0.0694, top-1 agreement 98.35% → 98.41%. Reviewers called the difference
  insignificant, and it was merged to match the reference. A behavioural claim made in the
  thread was **retracted by its author** for lack of a control, so there is no evidence of
  better answers.

### 3. CUDA thread-sync fixes on paths we use (in b10864)

- **#28475:** a missing `syncwarp` before reading a reduced value in `mm_ids_helper`, which
  groups tokens by expert during MoE prefill (`mmid.cu`), and in `mul_mat_f`/`_ids`
  (`mmf.cuh`). Found by `compute-sanitizer --tool racecheck`. **All our agentic models are
  MoE.**
- **#27870:** a thread barrier not reached by all threads in the f16 flash-attention kernel.
  3,232 sanitizer errors before, 0 after, speed unchanged. We use FA.
- Neither PR shows a wrong output. Both are undefined-behaviour fixes: a flakiness risk, not
  a measured accuracy loss.

### 4. Smaller, still ours

| change | in | who |
|---|---|---|
| gemma4 vision: dense layers kept causal on image tokens (was bidirectional, unlike HF); image-token budget 40–280 → **70–1120** (#28335) | 0.34.1 | `claude-ol-vision` (gemma4). Expect different OCR results and **more prompt tokens per image** |
| Qwen3-Coder tool-call parser: arguments whose schema is a union with `string` are now typed (`{"a":1}` becomes an object, `null` becomes null) instead of always raw strings (#28742) | **rc1 only** | Tiel, CyberTiel |
| context checkpoints no longer evicted before the list is full (#28302). Hybrid models otherwise re-prefill from an older checkpoint | 0.34.1 | only prompts < 8,192 tokens (`checkpoint_min_step`); Claude Code's prompt is far above that, and v4's cache-probe at 30k already prefilled only 517 new tokens |
| `/api/tags` 3.1 s → 294 ms; capabilities come from one metadata extract (#17858) | 0.34.1 | tooling (`head2head.sh` reads `capabilities`) |
| scheduler debug-log `LogValue` race (#18319) | 0.34.1 | log output only |

## Speed: checked, nothing applies

| change | why not for us |
|---|---|
| branchless Q4_K/Q5_K MMVQ unpack (#26705) | batch 1: −0.56% (Q4_K), +3.6% (Q5_K); gains only at batch ≥ 4–8 |
| MMVQ→MMQ crossover retune (#28285) | RTX 4090/5090 at batch 6–8, Jetson Orin; we decode at 1, MTP verifies 2–3 |
| multi-GPU CUDA graph-optimise pass (#28198) | **only with `GGML_CUDA_GRAPH_OPT=1`**; default unchanged. (`.67` having two GPUs is inferred in v1, never confirmed) |
| sparse flash attention (#27970) | DeepSeek-V4/GLM indexer only (`n_kv_max > 0`) |
| BF16 → F32 cuBLAS fallback (#28846) | NVIDIA **pre-Ampere** only. Tiel's UD-XL BF16 tensors are affected only if `.67`'s cards are Turing or older (unknown) |
| `GGML_CUDA_FA_QUANTS` replaces `FA_ALL_QUANTS` (#28079) | default still compiles f16, q8_0, q4_0 and bf16 KV kernels; no kernel lost |
| RAM peak at load (#27483) | CPU weight repacking; our models are 100% on GPU |
| cpp-httplib 0.54.1 → 0.56.0 (rc1) | WebSocket and server features; Ollama talks to `llama-server` on 127.0.0.1 |

## Checked, not ours

- **`preserve_reasoning` on by default (#28174):** a no-op for us. Ollama's
  `llamaServerChatMessage` never sends earlier thinking as `reasoning_content`, and Tiel's
  template already defaults `_preserve_thinking = true`.
- **Model graphs** (`qwen35moe`, `nemotron-h`, `cohere2moe`): refactors only
  (`n_ff_exp` → per-layer array, `build_qkv`), same math. `get_key_or_arr` fix (#28868)
  concerns a gemma4 line identical in b10760 and b10864, and our gemma4 loads.
- MTP KV over-allocation (#28630): north-mini has no NextN layers. Nemotron MTP crash guard
  (#28779): our Nemotron loads. Speculation after an image (#28715): no MTP plus vision in use.
- Deprecated `--mmap/--mlock/--dio` (#28334): Ollama passes `--load-mode`, which remains.
- Go dependencies: removals only (converter and tokenizer deleted), no version bumps. CUDA 13
  base image unchanged. The compat patch only adds `LLAMA_API` exports.

## Behaviour changes when updating (risks)

1. **Requests or `api/create` calls that set `typical_p` now fail** (#18448). Checked: no tag
   on `.67` and no script in this repo uses it.
2. **`ollama create` can no longer convert safetensors or quantize** (#14969). Checked:
   create-from-existing-model with `parameters` (our `-agentic` tags) is unchanged in
   `server/create.go`.
3. **Qwen outputs change by design (#2):** v4 gate and needle numbers for qwen35 models are
   not bit-comparable across the update.
4. **The runtime version is a variable** (v3). Finish v4 on 0.33.3, then update and re-run
   the control (`qwen3.6:35b-a3b` gen @2k, 130.04 tok/s) before comparing anything.
5. `.67` is shared, and its admin upgrades it. Ask for **0.34.1**. rc1 adds only #28742 for
   Tiel, plus fixes for models we don't run.

## `.37` (0.32.15): what is real

`.37` runs small models (qwen3.5:9b variants, qwen3:8b/14b, qwen3-vl:4b/8b, qwen3-coder:30b,
mistral-nemo, codestral). It gets everything above, plus the 0.33.x and b10488→b10760 range:

| change | applies on `.37` |
|---|---|
| `cache_read_input_tokens` reported on `/v1/messages` (ollama #17943) | observability only; the cache itself already worked |
| **model GGUF sampling defaults now honoured** (ollama #16471) | **behaviour change**: tags without baked sampler params may sample differently |
| qwen3-coder parser workarounds scoped to Qwen3-Coder; they slowed grammar with many tools (llama.cpp #27679) | Jinja-path models with Claude Code's large tool list |
| pillow-accurate image resize for all vision models (#27594) | qwen3-vl:4b/8b OCR |
| fused MoE expert reduction (#25952) | qwen3-coder:30b only (the one MoE) |
| cuBLAS static workspace, a crash fix on Volta/Turing plus CUDA graphs (#26574) | only if `.37` is Volta or Turing (unknown) |
| ~~0.33.0 "improved caching": prefill restore points, cancelled-prefill hang~~ | **not ours**: all `mlxrunner` commits (Apple Silicon) |
| ~~Claude Code token countdown fix~~ | **not ours via the server**: it is `ollama launch` config; see § Do now |

## Corrections to the first version of this file (commit 607dfcf)

- The repeat cut-off does **not** affect Tiel (the `Chat()` path has no repeat check). The
  trigger is 32 identical tokens, not 31.
- The GDN fix was oversold. The magnitude is small, and the behavioural claim in its thread
  was retracted.
- "f16 KV" was never verified. The measured KV cost (≥ 16.8 kB/token marginal) is above the
  f16 theoretical 10.2 kB/token for Tiel, so f16 is likely, but unconfirmed.
- The RAM-peak fix (#27483) is CPU-repack only, so it doesn't apply to us.
- The `.37` cache rework (0.33.0) is MLX-only, and the token-countdown fix is client-side.

## Sources

- Ollama: `llm/llama_server.go` (`Completion`, `Chat`, `llamaServerChatRequest`),
  `server/routes.go`, `server/images.go`, `server/create.go`, `server/sched.go`, `go.mod`,
  `LLAMA_CPP_VERSION` at v0.32.15 / v0.33.3 / v0.34.1 / v0.34.2-rc1; PRs #18374, #17858,
  #18319, #18448, #14969, #17943, #16471; commit `add1f92b`
- llama.cpp: `src/models/{qwen35moe,nemotron-h,cohere2moe,gemma4}.cpp`, `src/llama-graph.cpp`,
  `src/llama-kv-cache.cpp`, `ggml/src/ggml-cuda/{mmid.cu,mmf.cuh,mmvq.cu,fattn.cu,ggml-cuda.cu}`,
  `tools/server/server-context.cpp`, `common/parsers/qwen3-coder.cpp`, `common/arg.cpp`;
  PRs #28068, #28475, #27870, #28335, #28742, #28302, #28174, #26705, #28285, #28198, #27970,
  #28846, #28079, #27483, #28630, #28779, #28715, #28868, #28334, #27679, #27594, #25952, #26574
- Local: `results/kv-ladder-tiel.txt`, `review.md` R2, `~/.zshrc` `claude-ol*`,
  `../ollamaClaudeCode_v1/review.md` (two-GPU inference)
