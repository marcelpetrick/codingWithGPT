# v4 plan — Tiel-Coder, and the field re-measured on Ollama 0.33.3

Written **2026-09-17**, before any benchmark ran. The smoke tests in §1 are the only numbers
in this file. Results go to [`measurements.md`](measurements.md), the verdict to
[`README.md`](README.md).

The question is the same as in v1–v3: **which local model should drive Claude Code on
`192.168.100.67`?** This round's new candidate is
`Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest`, from
[peculiar-ragdoll/Tiel-Coder-35B-A3B-GGUF](https://huggingface.co/peculiar-ragdoll/Tiel-Coder-35B-A3B-GGUF).

---

## 1. What is already known (smoke tests, 2026-09-17)

| fact | value | source |
|---|---|---|
| `.67` runtime | **Ollama 0.33.3**. v3 was measured on 0.32.15 | `/api/version` |
| `.37` runtime | 0.32.15 (was 0.30.6 in v1/v2) | `/api/version` |
| what Tiel is | **Ornith-1.5-35B-A3B, re-quantized** (Unsloth Dynamic + own imatrix) and carrying the "Sharp" chat template. **Not a fine-tune**: the weights are Ornith-1.5's | HF model card |
| shape | `qwen35moe`, 34.7B, 256 experts / 8 used, 40 blocks, `full_attention_interval 4`, 262,144 native | `/api/show` |
| quant | UD-Q5_K_XL. The card benchmarked **UD-Q4_K_XL**, so our tier is one step above the vendor's own numbers | HF + tensors: Q8_0×256, Q5_K×78, Q6_K×38 |
| capabilities | `tools, thinking, completion, vision` (447M `qwen3vl_merger` projector) | `/api/show` |
| template | 30,505-char **Jinja** template `qwen3.8-froggeric-v22.5.0`, XML tool format. The Go `TEMPLATE` printed in the Modelfile is **not** the one used: thinking appears and tool calls parse | smoke test |
| shipped params | `temperature 0.6, top_k 20, top_p 0.95, min_p 0, num_ctx 262144, **presence_penalty 1.5**` | `/api/show` |
| residency @262144 | **34.13 GB, 100% GPU**. That leaves 1.43 GB below the 35.56 GB ceiling, the thinnest margin of any model measured | `/api/ps` |
| tool call, thinking disabled | `stop_reason tool_use`, exact args, 41 output tokens | `/v1/messages` |
| tool call, thinking default | thinking block + correct `tool_use`, 68 output tokens | `/v1/messages` |
| `think:false` on `/api/chat` | honoured (no thinking field) | `/api/chat` |

Vendor claims, **self-reported and not reproducible here**: SWE-bench-Live 12/25 (same as
"Opus 4.6 medium" per the card), Claw-Eval multi-turn 67.2 (base Ornith-1.5: 65.3),
MMLU-Pro 73.7 (base: 78.0). The card itself calls these one run per problem.

## 2. Why the old results are not enough — the gaps this round closes

v3's own first lesson was **"the runtime version is a variable"**: 0.32.9 → 0.32.15 moved
generation by 0% to +221% per model and re-ranked the field. `.67` has since moved again, to
**0.33.3**. That alone makes every v3 speed number non-comparable with anything measured today.
Reviewing v3's record turned up eight gaps:

| # | gap in the existing results | what v4 does about it |
|---|---|---|
| G1 | every speed number is from 0.32.15; `.67` is now 0.33.3 | re-run `tokrate` + residency for the **whole field still on the box**, same session as Tiel |
| G2 | Claude Code sessions are **n=1**. v3 itself showed the incumbent move 46 s → 58 s with no throughput change | **n=3** per model, report median and range |
| G3 | the session fixture is too easy: **19 of 19 sessions PASSed**, so it cannot separate models on capability | add a **harder multi-file fixture with hidden held-out tests** (scores overfitting and cheating, not just green/red) |
| G4 | ornith's 308 s session is **unexplained**. The thinking hypothesis was never tested (v3 §32) | record **output tokens and thinking volume per turn** from the transcript, and run Tiel + ornith with thinking on **and** off (`MAX_THINKING_TOKENS=0`) |
| G5 | vision was yes/no plus one qualitative screenshot read | scored vision bench: 3 fixtures, **25 objective checks**, reused from `../ollamaClaude_ImageProcessing`, on every vision-capable model, **at the full baked window**. Tiel's 1.43 GB margin may not hold an image workspace (qwen3-vl hit HTTP 500 exactly that way) |
| G6 | `cc-session.sh` wires only the Haiku slot; v3 later found subagents resolve `opus` and 404 | wire all four model slots, as the fixed aliases do |
| G7 | v1's `agentic-test.sh` unloads **every** resident model when it finishes, including a colleague's | v4 copy unloads only the model it tested |
| G8 | T1–T5 are single shots at the shipped temperature (v3 §19f) | full battery **×3** for Tiel; field ×1 with every non-PASS re-run 8× before it is believed |

## 3. The field

Everything still on `.67` that v3 recommended, rejected on a fixable ground, or needs as a
reference. One model resident at a time, server idle before every stage.

| # | tag | role in v4 |
|---|---|---|
| T1 | `Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest` | **the candidate, as shipped** (the tag you would actually use) |
| T2 | `tiel-coder:35b-q5-ctx256k-agentic` *(created)* | identical, but **`presence_penalty 0`**. v1 measured 1.5 as costing ~35% throughput on qwen. Shares the weight blob, costs 0 bytes of disk |
| F1 | `north-mini-code-1.0:q4_K_M-ctx256k-agentic` | v3 default |
| F2 | `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic` | v3 vision pick |
| F3 | `ornith:35b-ctx256k-agentic` | v3 deep-retrieval pick; **Ornith-1.0, Tiel's predecessor**, the closest control there is |
| F4 | `qwen3.6:35b-a3b-q4_K_M-agentic` | the long-running control (130.04 tok/s on both 0.32.x runtimes) |
| F5 | `nemotron-3.5-lightning:30b-ctx256k-agentic` | v3 524k-window pick |
| F6 | `nemotron-cascade-2:30b-ctx256k-agentic` | rejected on tool reliability. v3 said to "re-test if a tool-template fix ships", and a new runtime is the cheapest version of that |
| F7 | `qwen3.8:27b-q4_K_M-ctx128k-agentic` | the dense reference |

**Not re-measured, and why:** `granite4.2`, `gemma4:31b`, `laguna-xs-2.1` and `muse-glimmer`
are no longer on the box. `qwen3-vl:32b*` is an OCR model with a 49k window, not a Claude Code
driver (its own study is `../ollamaClaude_ImageProcessing`). `qwen3.6:27b*` served its purpose
as the Qwen3.8 stand-in. The Qwen3.8 MTP and q8 rungs were rejected in v3 on grounds a runtime
bump does not touch. **Not pulled:** Tiel's UD-Q4_K_XL (the vendor-benchmarked tier) and the
`-MTP` repo. Both are ≥22 GB onto a shared disk, and the Q5 tier is what was put on the box.

## 4. Stages

| stage | what | per model | tools |
|---|---|---|---|
| S0 | harness: copy v3 scripts, apply G6/G7, add `vision-bench.py`, `cc-session` hard fixture + token accounting | — | — |
| S1 | Tiel deep-dive: context ladder (65k/131k/262k), `tokrate` T1 vs T2, gates ×3, needle ladder to the cliff, vision at full window | ~40 min | `kv-probe`, `tokrate`, `agentic-test`, `needle-v2`, `vision-bench` |
| S2 | field on 0.33.3: `tokrate` + residency + gates ×1 (+ re-runs), needle spot-check at each model's previously deepest verified depth, vision where capable | ~15 min each | `head2head` |
| S3 | Claude Code end to end: easy + hard fixture, **n=3**, all models; thinking on/off for Tiel and ornith | ~2–3 h | `cc-session` |
| S4 | review: re-run anything anomalous, then write `measurements.md` and the verdict in `README.md` | — | — |

**Pre-registered rules**, fixed now so the results cannot pick them:

1. **Control drift.** If `qwen3.6:35b-a3b` generation @2k is within ±5% of 130.04, 0.33.3 is
   "speed-neutral for the control" and v3's cross-model deltas are only annotated. Outside
   ±5%, the version delta is reported as a finding and no 0.32.x speed number is ranked
   against a 0.33.3 one.
2. **Gates beat speed.** A model with a *reproducible* gate failure (≥3 of 8 re-runs) is not
   recommended as a default, whatever its speed. Same rule that rejected laguna and cascade-2.
3. **Tiel displaces north-mini as default only if** it passes 10/10 gates, is PASS on both
   fixtures in ≥ 2 of 3 runs, and its **median hard-fixture session** is no slower than
   north-mini's by more than the larger of the two models' ranges.
4. **Tiel takes the vision slot only if** it scores ≥ gemma4 on the 25 checks *at its baked
   262,144 window* (an image that only works at a smaller window is a different, smaller tag).
5. **`presence_penalty`.** If T2 is ≥10% faster than T1 on generation with no gate loss, the
   recommended tag is T2 and the shipped tag is documented as a trap.

## 5. Shared-server rules (unchanged from v2/v3)

- `idle.sh` waits out anything foreign, never evicts it. v4's copy adds the Tiel tags to
  `OURS` (you asked for Tiel to be benchmarked). For the one model under test it also accepts
  `--mine <tag>`, so the harness can unload a `qwen3.6` control **it loaded itself** without
  treating a colleague's `claude-ol2` session as ours.
- No deletes except `kvprobe-*` temp tags. T2 is kept (0 bytes) because it is the
  recommended form if rule 5 fires.

## 6. Commits

Atomic, on `master` like every earlier round: plan → harness → one commit per stage of
results → docs. Raw logs and fixture worktrees are git-ignored, same as v3. TSVs and
transcripts are committed.
