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
| — | `laguna-xs-2.1:q4_K_M` | **Not recommended.** Fastest challenger, and the only model that failed a gate. |
| — | `qwen3.8:27b` | **Could not be tested.** Requires Ollama ≥0.32.12; the box runs 0.32.9. |

## 2. Model identity

| | **qwen3.6-35b-a3b** | **laguna-xs-2.1** | **north-mini-code-1.0** | **gemma4-26b-a4b** | **qwen3.8-27b** |
|---|---|---|---|---|---|
| vendor | Alibaba / Qwen | Poolside | Cohere | Google DeepMind | Alibaba / Qwen |
| licence | Apache-2.0 | OpenMDW-1.1 | Apache-2.0 + AUP | Gemma terms | Apache-2.0 |
| status | incumbent | new | new | untested until now | **blocked** |
| built for | general + agentic | agentic coding | **agentic SWE** | general multimodal | agentic + pro work |

## 3. Architecture

| | qwen3.6-35b-a3b | laguna-xs-2.1 | north-mini-code | gemma4-26b-a4b | qwen3.8-27b |
|---|---|---|---|---|---|
| type | MoE | MoE | MoE | MoE | **dense** |
| total params | 36.0 B | 33.4 B | 30.5 B | 25.8 B | 27.3 B |
| **active / token** | **3 B** | **3 B** | **3 B** | ~4 B | **27.3 B (all)** |
| experts | — | 256 + 1 shared, 8 used | 128, 8 used | 128, 8 used | — |
| layers | — | 40 (10 global / 30 SWA) | 49 (3:1 SWA) | 30 + 27 vision | — |
| KV heads | — | 8 | 4 | — | — |
| quant | Q4_K_M | Q4_K_M | Q4_K_M | Q4_K_M | Q4_K_M |
| **vision** | **yes** | no | no | **yes** (+audio) | **yes** |

## 4. Memory and context — allocated vs *usable*

| | qwen3.6-35b-a3b | laguna-xs-2.1 | north-mini-code | gemma4-26b-a4b |
|---|---|---|---|---|
| weights on disk | 23.94 GB | 20.27 GB | 18.59 GB | **17.99 GB** |
| resident @262144 | 32.54 GB | 25.01 GB | **21.34 GB** | 22.15 GB |
| headroom left (of ~35.5) | 3.0 GB | 10.5 GB | **14.2 GB** | 13.4 GB |
| advertised context | 262144 | 262144 | 500000 | 262144 |
| **allocates @100% GPU** | 262144 | 262144 | **500000** (23.29 GB) | 262144 |
| **retrieval verified to** | **146,957** | 143,353 | 114,457 ⚠ | 143,324 |
| cold load | 17.3 s | **10.6 s** | 11.5 s | 14.4 s |

⚠ North-mini *allocates* 500,000 tokens but does not reliably retrieve across them — see §7.

## 5. Speed

| | qwen3.6-35b-a3b | laguna-xs-2.1 | north-mini-code | gemma4-26b-a4b |
|---|---|---|---|---|
| **generation** @2k words | **130.0 tok/s** | 119.5 | 83.6 | 70.0 |
| generation @20k words | **112.2 tok/s** | 93.5 | 78.2 | 65.4 |
| **prefill** @35k tokens | 3,911 tok/s | 4,882 | 4,331 | **5,740** |
| prefill vs incumbent | — | **+22%** | **+11%** | **+44%** |
| tokens per word | 1.755 | 1.711 | **1.358** | 1.710 |
| generation in **words/s** | **74.9** | 69.9 | 61.5 | 40.9 |

*Prefill is what an agentic loop pays on every turn (it re-reads context each time);
generation only covers the tokens the model emits. The tokeniser row matters: North-mini
packs ~21% more source into the same window, which narrows its generation deficit from 36%
to 18% in real terms.*

## 6. Capability gates — the decisive table

Seven gates against `/v1/messages`, the endpoint Claude Code actually uses.

| gate | what it proves | qwen3.6 | laguna | north-mini | gemma4 |
|---|---|---|---|---|---|
| T1 single tool | basic tool call | PASS | PASS | PASS | PASS |
| T2 tool selection | picks right tool of 4 | PASS | PASS | PASS | PASS |
| T3 multi-turn | consumes its own tool output | PASS | PASS | PASS | PASS |
| **T4 parallel calls** | two calls in one turn | PASS | **PARTIAL** ⚠ | PASS | PASS |
| T5 nested schema | real Claude Code tool shapes | PASS | PASS | PASS | PASS |
| T6 needle ×4 | window is real, not nominal | PASS ×4 | PASS ×4 | PASS ×4 | PASS ×4 |
| **T7 tools at depth** | tool call at ~50k context | PASS 3/3 | **FLAKY 2/3** ⚠ | PASS 3/3 | PASS 3/3 |
| **total** | | **10/10** | **8/10** | **10/10** | **10/10** |

**Why Laguna is not recommended despite being the fastest challenger.** T4: it emits one tool
call where two independent ones were offered — Claude Code batches by design, so every
serialised call costs a full round trip and erases its prefill advantage. T7: tool calling at
53,145 tokens passed twice and failed once; a *flaky* gate fails on turn three of a long
session, once the context is expensive to rebuild. Neither failure is visible in any
throughput benchmark.

## 7. End-to-end — real Claude Code sessions

Real `claude -p` against a repository with a genuine bug, scored from the repository
afterwards (tests green + source changed + test file untouched), not from the model's summary.

| | qwen3.6-35b-a3b | laguna-xs-2.1 | north-mini-code | gemma4-26b-a4b |
|---|---|---|---|---|
| verdict | **PASS** | **PASS** | **PASS** | **PASS** |
| wall clock | 46 s | **42 s** | 60 s | 60 s |
| turns | 16 | 18 | 22 | 16 |
| tools used | Bash×4 Read×3 Edit×1 | Bash×4 Read×2 Edit×1 | Read×5 Bash×5 Edit×1 | Bash×3 Read×2 Edit×2 |

All four produced a correct, idiomatic patch touching only the source file, and all read
before editing. **This test does not discriminate** — a one-file fix never needs parallel
tool calls and never reaches 53k context, so Laguna's failures could not surface. The gates
in §6 are what separate these models.

### North-mini's retrieval at depth

| prompt tokens | runs | result |
|---|---|---|
| 114,457 | 1 | **PASS** |
| 230,825 | 3 | **FAIL** (incl. pinned 500k window + 2048-token budget) |
| 347,193 | 3 | **PASS** — exact answer in 13 tokens |
| 398,089 | 1 | FAIL — restates the question |
| 456,281 | 1 | FAIL — *"the document does not contain…"* |

Non-monotonic and reproducible in both directions; unexplained. Two harness explanations
were tested and both ruled out. **Deploy at 262144, not 500000.** In its favour: when it
fails it *says so* — the previous deep-context pick (Nemotron) invented a plausible
passphrase instead, with no error and no signal.

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
`Qwen3.8-35B-A3B` is an unreleased leak. So on this hardware Qwen3.8 will always be **dense**,
and dense is the shape this box handles worst: a dense 27B measured **18.1 tok/s** here
against this MoE field's 70–130.

## 10. What matters, in order

1. **Tool-call reliability** — the only pass/fail property, and the reason the fastest
   challenger is rejected. Invisible in throughput benchmarks.
2. **Prefill speed** — paid on every turn of an agentic loop.
3. **Generation speed** — matters for plans and long edits; the number most over-weighted.
4. **Window size** — sharply diminishing returns. *Allocated ≠ usable.*

> **Useful window = min(allocated, retrieval-verified, affordable to prefill each turn).**
> For Claude Code, 262k of verified window beats 500k of nominal window.

**Operational note:** all three new models ship *without* a baked `num_ctx`, so as pulled none
is usable with Claude Code past 16,384 tokens — the endpoint silently drops the prompt tail
and stops calling tools. Each needs a variant with the window baked in. The good news: none
ships `presence_penalty` any more, which used to cost 31–35% of throughput.
