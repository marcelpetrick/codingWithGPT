# Local models for Claude Code — full comparison

**Hardware:** `192.168.100.67`, **35.56 GB** usable VRAM — measured, not the 40.4 GB on
paper, and reproduced to three decimals by two different model generations eight months
apart. **Runtime:** Ollama **0.32.15**. **Dates:** 2026-08-25 (on 0.32.9) and **2026-08-27**
(re-measured on 0.32.15). Server idle before every measurement, one model resident at a time.

> ### The runtime version is a variable, and it is the headline
>
> `.67` was upgraded from Ollama 0.32.9 to 0.32.15 between the two measurement days. **That
> re-ranked the field with no model changing.** Generation @2k: nemotron **+221%**,
> north-mini **+60%**, gemma4 **+49%** — and the control **0.0%**, 130.04 tok/s both times to
> two decimals.
>
> The control not moving is what makes this a finding rather than a warmer box or a changed
> harness. It also means **the previous edition of this document reached the right conclusion
> for a runtime that no longer exists**, and the recommendation below reverses it.
>
> Everything here was re-measured on 0.32.15 unless marked otherwise. Gates, residency and
> retrieval depth were re-checked and proved **version-stable** — north-mini's full T1–T7
> battery came back byte-identical, including every token count. Only speed moved.

---

## 1. Headline — what to use

| # | model | verdict |
|---|---|---|
| **1** | `north-mini-code-1.0:q4_K_M-ctx256k-agentic` @262144 | **Default driver.** Beats the former incumbent on generation, prefill, memory and retrieval depth, ties it on gates and end-to-end. **11.2 GB lighter.** No vision. |
| **2** | `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic` @262144 | **Vision, and read-heavy work.** Fastest prefill on the box (5,774) and the fastest end-to-end session measured (54 s), in 22.15 GB. |
| **3** | `nemotron-3.5-lightning:30b-ctx256k-agentic` | **Deep context only.** Now the fastest generator on the box (138.1, was 43.9) but the worst prefill, and it took 34 turns to do a 17-turn job. Holds **524,288** tokens, which nothing else does. |
| 4 | `qwen3.6:35b-a3b-q4_K_M-agentic` @262144 | **Superseded.** Still 10/10 and still has vision, but third on generation, third on prefill, and the heaviest thing on the box at 32.54 GB. |
| — | `qwen3.8:27b-q4_K_M` @131072 | **Measured, not recommended.** Capable — 9/10 gates, vision, best window-utilisation in the field — and **4.3× slower**. See §9. |
| — | `laguna-xs-2.1:q4_K_M` | **Not recommended, deleted.** The only model that failed a gate. Speed never re-measured on 0.32.15. |
| — | `muse-glimmer:30b-ctx128k-agentic` | **Not recommended, deleted.** Dense; never re-measured. |
| — | `qwen3.6:27b-q8_0-agentic` | **Not recommended.** Dense, 81,920 window, fabricates past it. |

**What changed since 2026-08-25:** the default. Not because north-mini improved, but because
the runtime upgrade made it 60% faster while leaving `qwen3.6:35b-a3b` exactly where it was.

## 2. The full field — one methodology

Ranked by generation speed, on **Ollama 0.32.15**. `MoE-3B` means a Mixture-of-Experts model activating ~3B
parameters per token; `dense` means every parameter is read for every token, which is the
shape this hardware handles worst.

| model | vendor | shape | gen @2k | prefill @35k | gates | window | resident | session |
|---|---|---|---|---|---|---|---|---|
| nemotron-3.5-lightning | NVIDIA | Mamba-2+MoE | **138.1** | 2,797 | **10/10** | **524,288** | 31.21 GB | 72 s |
| **north-mini-code-1.0** *(default)* | Cohere | MoE-3B | 132.9 | 4,443 | **10/10** | 262,144 | **21.34 GB** | 57 s |
| qwen3.6:35b-a3b *(former default)* | Alibaba | MoE-3B | 130.0 | 3,996 | **10/10** | 262,144 | 32.54 GB | 58 s |
| **gemma4:26b-a4b** *(vision)* | Google | MoE-4B | 104.1 | **5,774** | **10/10** | 262,144 | 22.15 GB | **54 s** |
| **qwen3.8:27b-q4** | Alibaba | **dense** | 30.4 | 1,428 | 9/10 | 131,072 | 26.24 GB | 111 s |
| qwen3.8:27b-q8 | Alibaba | **dense** | 19.4 | 1,487 | 8/10 | 65,536 | 32.82 GB | 137 s |
| *measured on 0.32.9 only:* | | | | | | | | |
| laguna-xs-2.1 ✗ | Poolside | MoE-3B | *119.5* | *4,882* | **8/10** | 262,144 | 25.01 GB | *42 s* |
| qwen3.6:27b-q4 *(dense proxy)* | Alibaba | **dense** | *31.0* | *1,307* | 9/10 | 131,072 | 30.17 GB | *140 s* |
| muse-glimmer:30b ✗ | — | **dense** | *28.5* | *1,963* | 10/10 * | 131,072 | 19.45 GB | *160 s* |
| qwen3.6:27b-q8 | Alibaba | **dense** | *19.5* | *1,464* | 9/10 | 81,920 | 34.03 GB | *179 s* |

✗ = deleted from the box after measurement (see §11). \* = see §6 note on Muse's gate score.
*Italic* speed figures are **0.32.9 numbers that were never re-measured** — given that three
of four re-measured models moved by 49–221%, treat them as unknown rather than as slow. Their
gate scores stand, because gates proved version-stable.

**The single clearest line in this table is still the shape column.** Every MoE sits at
104–138 tok/s and finishes end to end in 54–72 s; every dense model sits at 19–30 and takes
111–179 s. Ten models deep, no exception. This is a memory-bandwidth machine: a dense model
re-reads all 27B parameters for every token it writes, an MoE reads ~3B.

**The top four are tied end to end at 54–58 s** — and the former incumbent's session moved
46 s → 58 s while its throughput did not move at all, which is the clearest evidence
available that this metric carries real run-to-run variance. A four-second gap between two
models in that column means nothing. Nemotron's 72 s is outside the band for a reason the
transcript shows: **34 turns to do a job the others did in 16–19.**

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
| **retrieval verified to** | **146,957** | **201,737** | 143,324 | **161,516** | 72,419 | 72,419 |
| KV bytes / token | — | — | — | — | **64,784** | — |

**Dense KV costs 4× more per token.** Measured on `qwen3.6:27b-q4`: 64,784 bytes/token
against Laguna's 16,384. That is why the dense models have the *smallest* windows here
despite being mid-sized — and why the q8 tops out at 81,920.

## 5. Speed

On **0.32.15**, with the 0.32.9 figure alongside to show what the runtime alone was worth:

| | gen @2k | *was (0.32.9)* | delta | gen @20k | prefill @35k |
|---|---|---|---|---|---|
| nemotron-3.5-L | **138.1** | *43.9* | **+221%** | **144.9** | 2,797 |
| north-mini-code | 132.9 | *83.6* | **+60%** | 113.0 | 4,443 |
| qwen3.6:35b-a3b | 130.0 | *130.0* | **0.0%** | 112.1 | 3,996 |
| gemma4:26b-a4b | 104.1 | *70.0* | **+49%** | 92.6 | **5,774** |
| **qwen3.8:27b-q4 (dense)** | **30.4** | — | — | 27.4 | 1,428 |
| qwen3.8:27b-q8 (dense) | 19.4 | — | — | 18.2 | 1,487 |

*Prefill is what an agentic loop pays every turn (it re-reads context each time); generation
covers only the tokens the model emits. The dense models lose on **both**: 1,428 tok/s
prefill against north-mini's 4,443.*

**The 0.32.15 optimisation is in the decode path, not the prefill path.** Prefill barely
moved for anyone — gemma4 +0.6%, north-mini +1.2%, the control +2.2%, nemotron −8.3% — while
generation moved by up to 221%. Both outliers were run twice and reproduce (nemotron 140.8
then 135.5; north-mini 133.7 then 132.0).

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

### North-mini's retrieval at depth — the one anomaly this report cannot explain

It *allocates* 500,000 tokens in 23.29 GB. It does not retrieve across all of them.

| prompt tokens | runs | result |
|---|---|---|
| 114,457 · 172,649 · **201,737** | 3 | **PASS** — each answering in 13 tokens |
| **230,825** | **5** | **FAIL** — every time |
| **347,193** | 3 | **PASS** — every time |
| 398,089 · 456,281 | 2 | FAIL |

Reliable retrieval reaches **201,737 tokens**. Past that the result inverts and stays
inverted: 230,825 fails five times out of five, while 347,193 — deeper — passes three out of
three. Four explanations were tested and all four are dead: the generation budget (re-run at
2048 and 4096), the harness's request-window sizing (re-sent pinned to 500,000), the baked
window itself (the identical document fails on the 262,144 variant too), and leaked reasoning
(with `think:true` the `thinking` field is empty and the passphrase appears nowhere).

**Practical consequence: deploy at `num_ctx 262144`.** The ~200k reliable ceiling sits above
anything Claude Code will ask of it — the alias caps context at 200,000 — so the anomaly is
documented rather than load-bearing. When it does fail past that, it *reports* failure
("the document does not contain…") rather than inventing an answer, which the previous
deep-context pick did.

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

## 9. Qwen3.8 — measured

The blocker is gone. Every Qwen3.8 manifest declares `"requires":"0.32.12"` and the box ran
0.32.9, so the registry refused the pull with **HTTP 412** before any data moved. On
2026-08-27 `.67` was upgraded to **0.32.15** and all three rungs ran. Every rung is q4_K_M or
q8_0 — no sub-4-bit quantisation was pulled or considered.

| rung | window @100% GPU | resident | gen @2k | prefill @35k | gates | session |
|---|---|---|---|---|---|---|
| `qwen3.8:27b-q4_K_M` | **131,072** | 26.24 GB | **30.4** | 1,428 | 9/10 | PASS 111 s |
| `qwen3.8:27b-mtp-q4_K_M` | 131,072 | 26.24 GB | 36.6 | **767** | — | PASS 109 s |
| `qwen3.8:27b-q8_0` | 65,536 | 32.82 GB | 19.4 | 1,487 | 8/10 | PASS 137 s |

**The verdict: a good model in the wrong shape for this box.** It is 4.3× slower than the
default and finishes the end-to-end fixture in 111 s against the field's 54–58 s.

### 9a. The prediction was right, and here is the receipt

The previous edition of this document could not test Qwen3.8, so it measured
`qwen3.6:27b-q4_K_M` as a proxy — same vendor, same dense 27B shape, same quantisation — and
committed to a prediction in writing:

> *"Qwen3.8-27B on this box should land near **30 tok/s**, take roughly **3× longer** per
> task, and **fail to fit its advertised 256K window at 100% GPU** — expect to bake it at
> 131,072."*

| predicted | measured |
|---|---|
| ~30 tok/s | **30.4 tok/s** |
| ~3× longer per task | **2.4×** (111 s vs 46 s), 1.9× against the current default |
| will not hold 256K; bake at 131,072 | **262,144 spills to 96% GPU; baked at 131,072** |

Three for three. The q8 rung repeated the trick: the predecessor measured 19.5 tok/s,
Qwen3.8's q8 measured **19.41**.

**This is the strongest single result in the report.** A model's *architecture class* — how
many parameters it activates per token — predicted its performance on this hardware to within
2%, across a full model generation, before the model could even be downloaded. Vendor
benchmark gains (Terminal-Bench 2.1 63.4 → 73.0) did not move that number at all.

### 9b. Where Qwen3.8 is genuinely good

It did not fail. Reported because the speed verdict would otherwise misrepresent it:

- **Tool calling is sound.** T4 (parallel calls) and T7 (3/3 at 53,283 tokens) both pass —
  the two gates that disqualified `laguna-xs-2.1`. T5 held **11/11** on re-run.
- **Best window utilisation in the field.** Verified retrieval to **119,015** of 131,072
  baked = **90.8%**, against north-mini's 40% and the former incumbent's 56%. Its window is
  the smallest here and the most completely usable.
- **It drives Claude Code correctly** — tool histogram *identical* to the incumbent's
  (`Bashx4,Readx3,Editx1`), fixed the source and not the test.
- **Vision works and is accurate**, not merely capability-flagged.

### 9c. Two footguns, if you use it anyway

**Pull `qwen3.8:27b-q4_K_M`, never `qwen3.8:27b`.** The bare tag's params digest is
byte-identical to the MTP build, so the name a person naturally types silently enables
speculative decoding. On Qwen3.8 that is **+20% generation for −46% prefill** — a net loss on
a large prompt (28.9 s vs 50.9 s on a 35k-token turn) and a wash on a small one (session
111 s vs 109 s). An agentic loop lives at the large end.

**It is not naive-dense, which is the one thing the proxy got wrong.**
`full_attention_interval 4` means only **18 of 65 layers** hold full KV: **73,730 bytes per
token** against 266,240 naive, 3.6× cheaper. Measured three times across both quantisations,
reproducing to the byte. Without it a dense 27B could not hold 131k on this box at all — so
the "dense punishes you" intuition was right about speed and wrong about memory.

## 10. What matters, in order

0. **The runtime version.** New to this list, and it outranks everything below it: an Ollama
   point upgrade changed generation throughput by **0% to +221% depending on the model** and
   re-ranked the field with no model changing. A tok/s figure without a runtime version
   attached is not a result. Capability, memory and retrieval depth proved version-stable;
   only speed moved.
1. **Tool-call reliability** — the only pass/fail property, and the reason the fastest
   challenger is rejected. Invisible in throughput benchmarks.
2. **Prefill speed** — paid on every turn of an agentic loop.
3. **Generation speed** — matters for plans and long edits; the number most over-weighted.
4. **Window size** — sharply diminishing returns. *Allocated ≠ usable.*

> **Useful window = min(allocated, retrieval-verified, affordable to prefill each turn).**
> For Claude Code, 262k of verified window beats 500k of nominal window.

**5. Model shape decides all of the above.** On 0.32.15 every MoE runs 104–138 tok/s and
finishes the task in 54–72 s; every dense model runs 19–30 tok/s and takes 111–179 s. Ten
models deep, no exception — and §9a is the proof, where shape predicted an untested model's
speed to within 2%. On a memory-bandwidth-bound box, active parameters per token is the
number that predicts everything else.

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
