# Local models for Claude Code — full comparison

**Hardware:** `192.168.100.67`, ≈35.5 GB usable VRAM (measured, not the 40.4 GB on paper).
**Runtime:** Ollama 0.32.9. **Date:** 2026-08-25. Server idle before every measurement, one
model resident at a time. Control re-measured in the same session; it reproduced the previous
run to within 2%.

---

## 1. Headline — what to use

| # | model | verdict |
|---|---|---|
| **1** | `qwen3.6:35b-a3b-q4_K_M-agentic` @262144 | **Default driver.** Fastest generation, clean on every gate, deepest retrieval, has vision. Unchanged from the previous round. |
| **2** | `north-mini-code-1.0:q4_K_M-ctx256k-agentic` | **Deep-context option.** Replaces Nemotron: 8 GB lighter, 1.9× faster, same gate score, reports failure instead of inventing answers. |
| **3** | `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic` | **Read-heavy / vision niche.** Fastest prefill on the box (+44%), 10/10 gates — but 47% slower to generate. |
| 4 | `nemotron-3.5-lightning:30b-ctx256k-agentic` | **Superseded but kept.** Only model holding 524,288 tokens; 2.6× slower than north-mini for the same job. |
| — | `qwen3.6:27b-q4_K_M-ctx128k-agentic` | **Reference only** — the dense proxy for the untestable Qwen3.8. 4.2× slower than the incumbent. |
| — | `laguna-xs-2.1:q4_K_M` | **Not recommended, deleted.** Fastest challenger, and the only model that failed a gate. |
| — | `muse-glimmer:30b-ctx128k-agentic` | **Not recommended, deleted.** 4.6× slower than the incumbent with half the window. |
| — | `qwen3.6:27b-q8_0-agentic` | **Not recommended.** Slowest measured (18.1 tok/s), 81,920 window, fabricates past it. |
| — | `qwen3.8:27b` | **Could not be tested.** Requires Ollama ≥0.32.12; the box runs 0.32.9. |

## 2. The full field — eight models, one methodology

Ranked by generation speed. `MoE-3B` means a Mixture-of-Experts model activating ~3B
parameters per token; `dense` means every parameter is read for every token, which is the
shape this hardware handles worst.

| model | vendor | shape | gen @2k | prefill @35k | gates | window | resident | session |
|---|---|---|---|---|---|---|---|---|
| **qwen3.6:35b-a3b** *(default)* | Alibaba | MoE-3B | **130.0** | 3,911 | **10/10** | 262,144 | 32.54 GB | **46 s** |
| laguna-xs-2.1 ✗ | Poolside | MoE-3B | 119.5 | 4,882 | **8/10** | 262,144 | 25.01 GB | **42 s** |
| **north-mini-code-1.0** *(deep ctx)* | Cohere | MoE-3B | 83.6 | 4,331 | **10/10** | 262,144 | **21.34 GB** | 60 s |
| **gemma4:26b-a4b** *(prefill)* | Google | MoE-4B | 70.0 | **5,740** | **10/10** | 262,144 | 22.15 GB | 60 s |
| nemotron-3.5-lightning | NVIDIA | Mamba-2+MoE | 43.9 | 3,050 | **10/10** | **524,288** | 31.21 GB | 113 s |
| qwen3.6:27b-q4 *(dense proxy)* | Alibaba | **dense** | 31.0 | 1,307 | 9/10 | 131,072 | 30.17 GB | 140 s |
| muse-glimmer:30b ✗ | — | **dense** | 28.5 | 1,963 | 10/10 * | 131,072 | 19.45 GB | 160 s |
| qwen3.6:27b-q8 | Alibaba | **dense** | 19.5 | 1,464 | 9/10 | 81,920 | 34.03 GB | **179 s** |

✗ = deleted from the box after measurement (see §11). \* = see §6 note on Muse's gate score.

**The single clearest line in this table is the shape column.** Every MoE sits at 70–130
tok/s; every dense model sits at 19–31. The four dense models are also the four slowest
end-to-end sessions. This is a memory-bandwidth machine: a dense model re-reads all 27B
parameters for every token it writes, an MoE reads ~3B.

## 3. Architecture

| | qwen3.6-35b-a3b | north-mini-code | gemma4-26b-a4b | nemotron-3.5-L | qwen3.6-27b (dense) | qwen3.8-27b |
|---|---|---|---|---|---|---|
| type | MoE | MoE | MoE | Mamba-2 hybrid | **dense** | **dense** |
| total params | 36.0 B | 30.5 B | 25.8 B | 32.9 B | 27.8 B | 27.3 B |
| **active / token** | **3 B** | **3 B** | ~4 B | **3 B** | **all** | **all** |
| experts | — | 128, 8 used | 128, 8 used | — | — | — |
| licence | Apache-2.0 | Apache-2.0 +AUP | Gemma terms | NVIDIA OM | Apache-2.0 | Apache-2.0 |
| **vision** | **yes** | no | **yes** | no | **yes** | **yes** |

## 4. Memory and context — allocated vs *usable*

| | qwen3.6-35b-a3b | north-mini | gemma4 | nemotron | qwen3.6-27b-q4 | qwen3.6-27b-q8 |
|---|---|---|---|---|---|---|
| weights | 23.94 GB | 18.59 GB | **17.99 GB** | 25.43 GB | 17.42 GB | 29.97 GB |
| max window @100% GPU | 262,144 | **500,000** | 262,144 | **524,288** | **131,072** | **81,920** |
| resident there | 32.54 GB | 23.29 GB | 22.15 GB | 31.21 GB | 30.17 GB | 34.03 GB |
| **retrieval verified to** | **146,957** | 114,457 | 143,324 | **161,516** | 72,419 | 72,419 |
| KV bytes / token | — | — | — | — | **64,784** | — |

**Dense KV costs 4× more per token.** Measured on `qwen3.6:27b-q4`: 64,784 bytes/token
against Laguna's 16,384. That is why the dense models have the *smallest* windows here
despite being mid-sized — and why the q8 tops out at 81,920.

## 5. Speed

| | gen @2k | gen @20k | prefill @35k | vs incumbent (gen) |
|---|---|---|---|---|
| qwen3.6:35b-a3b | **130.0** | **112.2** | 3,911 | — |
| laguna-xs-2.1 | 119.5 | 93.5 | 4,882 | −8% |
| north-mini-code | 83.6 | 78.2 | 4,331 | −36% |
| gemma4:26b-a4b | 70.0 | 65.4 | **5,740** | −46% |
| nemotron-3.5-L | 43.9 | 44.9 | 3,050 | −66% |
| **qwen3.6:27b-q4 (dense)** | **31.0** | 27.8 | 1,307 | **−76%** |
| muse-glimmer | 28.5 | 27.9 | 1,963 | −78% |
| qwen3.6:27b-q8 (dense) | 19.5 | 18.1 | 1,464 | **−85%** |

*Prefill is what an agentic loop pays every turn (it re-reads context each time); generation
covers only the tokens the model emits. Note the dense models lose on **both**: 1,307 tok/s
prefill against the incumbent's 3,911.*

## 6. Capability gates

Seven gates against `/v1/messages`, the endpoint Claude Code actually uses.

| gate | qwen3.6-a3b | laguna | north-mini | gemma4 | nemotron | 27b-q4 | muse | 27b-q8 |
|---|---|---|---|---|---|---|---|---|
| T1 single tool | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| T2 tool selection | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| T3 multi-turn | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| **T4 parallel calls** | PASS | **PARTIAL** | PASS | PASS | PASS | PASS | PASS | PASS |
| T5 nested schema | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| T6 needle ×4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | **3/4** | 4/4 * | **3/4** |
| **T7 tools at depth** | PASS | **FLAKY** | PASS | PASS | PASS | PASS | PASS | PASS |
| **total** | **10/10** | **8/10** | **10/10** | **10/10** | **10/10** | 9/10 | 10/10 * | 9/10 |

**Laguna** is the only model to fail on *capability*: it serialises parallel tool calls (T4),
and tool calling at 53,145 tokens passed twice then failed once (T7). A flaky gate fails on
turn three of a long session, after context is expensive to rebuild — worse to live with than
an outright failure, and invisible in any throughput benchmark.

**The two dense 9/10 scores are window failures, not capability failures.** Both lost T6 at
the 120k depth because the document exceeds their window — and both then answered *wrongly
rather than erroring*: the q4 returned `'standard policy'` (filler text) at
`prompt_eval=65538`, exactly half its 131,072 window; the q8 returned `'5276'` at
`prompt_eval=40962`, exactly half its 81,920. That is the silent-halving cliff, and the
answer it produces is a fabrication.

**\* Muse's asterisk.** Its raw `agentic-test.sh` T6 rows read FAIL, but that is v1's
`num_predict 64` artifact — Muse needs ~70 tokens to emit the passphrase and the log shows
`eval=70–84`. Re-tested with a 512-token budget it passes all four depths to 114,487 tokens.
Scoring it 6/10 on the raw rows would misrepresent it.

## 7. End-to-end — real Claude Code sessions

Real `claude -p` against a repository with a genuine bug, scored from the repository
afterwards (tests green + source changed + test file untouched), not from the model's summary.

| model | verdict | wall clock | turns | tools |
|---|---|---|---|---|
| laguna-xs-2.1 | PASS | **42 s** | 18 | Bash×4 Read×2 Edit×1 |
| qwen3.6:35b-a3b | PASS | 46 s | 16 | Bash×4 Read×3 Edit×1 |
| north-mini-code | PASS | 60 s | 22 | Read×5 Bash×5 Edit×1 |
| gemma4:26b-a4b | PASS | 60 s | 16 | Bash×3 Read×2 Edit×2 |
| nemotron-3.5-L | PASS | 113 s | 24 | Read×5 Bash×4 Edit×1 |
| **qwen3.6:27b-q4 (dense)** | PASS | **140 s** | 16 | Bash×4 Read×3 Edit×1 |
| muse-glimmer | PASS | 160 s | 20 | Bash×5 Read×4 Edit×1 |
| qwen3.6:27b-q8 (dense) | PASS | **179 s** | 15 | Bash×4 Read×2 Edit×1 |

**All eight pass.** Every one read the failing test, edited only the source, re-ran the suite,
and produced a correct even/odd branch. None blind-wrote the file. Capability is not what
separates these models on a task this size.

**What separates them is 4.3× of wall clock** — 42 s to 179 s for identical work. With eight
models the pattern the four-model table could not show is unmistakable: the four MoE models
finish in 42–60 s, the four dense/hybrid models take 113–179 s. On a one-file fix that is a
minute versus three; on a day of real work it is the whole difference.

## 8. Vendor benchmark claims — self-reported, for context only

Not run by us. Harness versions differ between vendors, so these are **not** comparable
across columns.

| model | claimed |
|---|---|
| `qwen3.8-27b` | Terminal-Bench 2.1 **73.0** · SWE-bench Pro **61.7** · LiveCodeBench v6 **90.3** · OSWorld 84.3 |
| `qwen3.6-27b` (prior gen) | Terminal-Bench 2.1 63.4 · SWE-bench Pro 53.5 · LiveCodeBench v6 83.9 |
| `laguna-xs-2.1` | SWE-bench Verified **70.9%** · Multilingual 63.1% · SWE-Bench Pro 47.6% · Terminal-Bench 2.0 37.5% |
| `north-mini-code-1.0` | Artificial Analysis Coding Index **33.4** |
| `gemma4-26b-a4b` | MMLU Pro **82.6%** · LiveCodeBench v6 **77.1%** |

## 9. Why Qwen3.8 is absent

Every Qwen3.8 manifest declares `"requires":"0.32.12"`. The box runs **0.32.9**, so the
registry refuses the pull with **HTTP 412** before any data transfers. The upgrade to 0.32.15
has been requested from the machine's owner. The benchmark harness is built and waiting.

There is also **no faster Qwen3.8 to wait for**: Qwen published exactly two shapes — the dense
27B, and a 2.4T-A95B "Max" at ~1.2 TB (34× this hardware). The widely-discussed
`Qwen3.8-35B-A3B` is an unreleased leak. So on this hardware Qwen3.8 will always be **dense**.

### 9a. What a dense 27B actually does here — measured, not guessed

`qwen3.6:27b-q4_K_M` is the same vendor, the same 27B dense shape and the same Q4_K_M
quantisation as `qwen3.8:27b-q4_K_M` (17.42 GB of weights against Qwen3.8's 17.74 GB). It is
therefore the closest available proxy, and it was measured from scratch for this report:

| | dense 27B q4 *(proxy)* | qwen3.6:35b-a3b *(incumbent)* | ratio |
|---|---|---|---|
| generation @2k | **31.0 tok/s** | 130.0 | **4.2× slower** |
| prefill @35k | **1,307 tok/s** | 3,911 | **3.0× slower** |
| max window @100% GPU | **131,072** | 262,144 | **half** |
| KV bytes per token | **64,784** | — (MoE ≈16,384) | **4× heavier** |
| end-to-end session | **140 s** | 46 s | **3.0× slower** |
| tool gates | 9/10 (window) | 10/10 | — |

**The prediction this yields for Stage A**, stated as a prediction so it can be checked:
Qwen3.8-27B on this box should land near **30 tok/s**, take roughly **3× longer** per task,
and **fail to fit its advertised 256K window at 100% GPU** — expect to bake it at 131,072.

That is the trade to put in front of anyone asking for Qwen3.8: its vendor benchmarks are
genuinely stronger (Terminal-Bench 2.1 73.0 against 63.4), but on this hardware it arrives
~4× slower in a half-sized window. Smarter per token, far fewer tokens per second — and an
agentic loop spends its life in tool round-trips, not in single brilliant completions.

## 10. What matters, in order

1. **Tool-call reliability** — the only pass/fail property, and the reason the fastest
   challenger is rejected. Invisible in throughput benchmarks.
2. **Prefill speed** — paid on every turn of an agentic loop.
3. **Generation speed** — matters for plans and long edits; the number most over-weighted.
4. **Window size** — sharply diminishing returns. *Allocated ≠ usable.*

> **Useful window = min(allocated, retrieval-verified, affordable to prefill each turn).**
> For Claude Code, 262k of verified window beats 500k of nominal window.

**5. Model shape decides all of the above.** Every MoE measured here runs 70–130 tok/s and
finishes the end-to-end task in 42–60 s; every dense model runs 19–31 tok/s and takes
113–179 s. On a memory-bandwidth-bound box, active parameters per token is the number that
predicts everything else.

**Operational note:** every model here ships *without* a baked `num_ctx`, so as pulled none
is usable with Claude Code past 16,384 tokens — the endpoint silently drops the prompt tail
and stops calling tools. Each needs a variant with the window baked in. The good news: none
of the new arrivals ships `presence_penalty` any more, which used to cost 31–35% of
throughput.

## 11. Housekeeping — what was removed from the box

Ollama tags **share weight blobs**: six tags pointing at one 22.29 GiB model are 22.29 GiB on
disk, not 133. Summing `/api/tags` sizes therefore triple-counts. Real footprint before this
cleanup was **215.09 GiB**, not the 653.51 GiB a naive sum reports.

Deleted, 9 tags, after all their measurements were taken and committed:

| removed | freed |
|---|---|
| `qwen3.6:27b-mtp-q8_0` ×3 — dense q8 + MTP draft head, never recommended | 27.92 GiB |
| `laguna-xs-2.1` ×2 — the 8/10 gate score | 18.88 GiB |
| `muse-glimmer:30b` ×2 — 4.6× slower than the incumbent, half the window | 16.91 GiB |
| `qwen3.5:9b` ×2 — superseded generation | 6.14 GiB |
| **total** | **69.85 GiB** |

Result: **215.09 → 145.24 GiB**, 32 → 23 tags. Every deleted model is re-pullable in ~10
minutes and all their numbers are preserved in this report. Kept by explicit decision: the
whole `nemotron-3.5-lightning` family, every non-MTP `qwen3.6` tag, and
`qwen3.6:35b-a3b-mtp-q4_K_M` — which runs 129 tok/s at 28.89 GB resident, 3.65 GB lighter
than the incumbent, and remains the best speed-per-GB option on the box.
