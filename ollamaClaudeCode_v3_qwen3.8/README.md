# Which local model should drive Claude Code? — the 2026-08 field

Measured on **`192.168.100.67`** (Ollama **0.32.9**, ≈35.5 GB usable), 2026-08-25. Server
asserted idle before every measurement, one model resident at a time.

[`measurements.md`](measurements.md) holds every number and how it was taken;
[`model_cards.md`](model_cards.md) is one card per model; [`market_research.md`](market_research.md)
is the survey of what exists; [`plan.md`](plan.md) is what we set out to do. This is the summary.

---

## The verdict

**Keep `qwen3.6:35b-a3b-q4_K_M-agentic` at `num_ctx 262144`. Nothing in the 2026-08 field
displaced it.**

One thing does change: **the deep-context slot moves from Nemotron to
`north-mini-code-1.0`,** and it is a clear win — same job, 8 GB less memory, 1.9× the speed.

| | model | why, in one line |
|---|---|---|
| **default** | `qwen3.6:35b-a3b-q4_K_M-agentic` @ 262144 | still the fastest generator on the box, 10/10 gates, retrieves deepest, and has vision |
| **deep context** | `north-mini-code-1.0:q4_K_M-ctx256k-agentic` | 10/10 gates at **21.34 GB** where Nemotron needed 31.21, and **1.9× faster**. Replaces `claude-ol-nemo` |
| **prefill / vision** | `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic` | the fastest prefill measured here (5,740 tok/s, +44%), 10/10 gates, vision — but 47% slower to generate |
| **deepest window** | `nemotron-3.5-lightning:30b-ctx256k-agentic` | kept: the only model holding 524,288 tokens and retrieving to 161,516 — but 2.6× slower than north-mini for ordinary deep-context work |
| **reference only** | `qwen3.6:27b-q4_K_M-ctx128k-agentic` | the dense stand-in for the blocked Qwen3.8 — 4.2× slower than the incumbent, half the window |
| **not recommended** | `laguna-xs-2.1` *(deleted)* | fastest challenger (119.5 tok/s) and **the only model that failed a gate** |
| **not recommended** | `muse-glimmer:30b` *(deleted)*, `qwen3.6:27b-q8_0` | dense: 28.5 and 19.5 tok/s, 160 s and 179 s end to end |
| **unmeasured** | `qwen3.8:27b` | **blocked**: needs Ollama ≥0.32.12, `.67` runs 0.32.9 |

## Qwen3.8: what actually happened

The project was commissioned to benchmark it, and it could not be benchmarked. Stated
plainly rather than buried:

**`.67` cannot pull it.** Every Qwen3.8 manifest carries `"requires":"0.32.12"`; the box runs
0.32.9 and the registry refuses with **HTTP 412** before a byte moves. The upgrade to 0.32.15
has been requested from the box's owner and had not happened as of 2026-08-25. The harness is
built and waiting; Stage A runs the day the box is upgraded.

**And there is no faster Qwen3.8 to wait for.** Qwen published exactly two shapes: the dense
27B, and `Qwen3.8-2.4T-A95B` (Max) at ~1.2 TB in FP8 — 34× this box. The `Qwen3.8-35B-A3B`
the community is asking for is **a leak, not a release**. So on this hardware the dense 27B
is the only Qwen3.8 there will ever be, and the open question is not *which tag* but whether
a dense 27B is fast enough here at all. v2 measured the dense 27B q8 at **18.1 tok/s** against
this MoE field's 70–130. That is the question Stage A exists to settle.

## The eight models, measured identically

| | **incumbent** *(control)* | **laguna-xs-2.1** | **north-mini-code** | **gemma4:26b-a4b** |
|---|---|---|---|---|
| vendor | Alibaba | Poolside | Cohere | Google DeepMind |
| shape | 36B MoE, 3B active | 33B MoE, 3B active | 30B MoE, 3B active | 26B MoE, 4B active |
| **generation** @2k | **130.0 tok/s** | 119.5 | 83.6 | 70.0 |
| **prefill** @35k | 3,911 tok/s | 4,882 | 4,331 | **5,740** |
| resident @262144 | 32.54 GB | 25.01 GB | **21.34 GB** | 22.15 GB |
| max window @100% GPU | 262144 | 262144 | **500000** (allocates) | 262144 |
| **tool gates T1–T7** | **10/10** | **8/10** | **10/10** | **10/10** |
| needle @160k | PASS @ 146,957 | PASS @ 143,353 | PASS @ 114,457 | PASS @ 143,324 |
| Claude Code session | PASS 46 s | PASS 42 s | PASS 60 s | PASS 60 s |
| vision | **yes** | no | no | **yes** |

### And the four reference models

| | **nemotron-3.5-L** | **qwen3.6:27b-q4** *(dense)* | **muse-glimmer** | **qwen3.6:27b-q8** *(dense)* |
|---|---|---|---|---|
| shape | Mamba-2 + MoE, 3B active | **dense 27B** | **dense 30B** | **dense 27B** |
| **generation** @2k | 43.9 tok/s | 31.0 | 28.5 | **19.5** |
| **prefill** @35k | 3,050 | 1,307 | 1,963 | 1,464 |
| max window @100% GPU | **524,288** | 131,072 | 131,072 | **81,920** |
| resident there | 31.21 GB | 30.17 GB | **19.45 GB** | 34.03 GB |
| tool gates | **10/10** | 9/10 | 10/10 * | 9/10 |
| needle | **161,516** | 72,419 | 114,487 | 72,419 |
| Claude Code session | 113 s | 140 s | 160 s | **179 s** |

**All eight drive Claude Code through a real single-file fix.** Every one read the failing
test, edited only the source, re-ran the suite, and produced a correct patch. Capability is
flat across the whole field on a task this size — but wall clock is not: **42 s to 179 s,
4.3× for identical work**, and the split falls exactly on architecture. Every MoE finishes in
42–60 s; every dense or hybrid model takes 113–179 s.

That is the answer to "is a dense 27B fast enough here" — and therefore the best available
answer about Qwen3.8, which is dense and cannot be run on this box.

## What actually matters, in order

The measurements disagree with the intuition that a bigger window and a bigger tok/s number
are what to shop for.

**1. Tool-call reliability, and it is not close.** It is the only property that is pass/fail
rather than a gradient. Laguna is the fastest challenger and is not recommended, because it
serialises parallel tool calls (T4) and dropped one call in three at 53,145 tokens (T7).
A model that is 9% faster and breaks the loop on turn three is a worse tool, not a faster
one — and **neither failure appears in any throughput benchmark.**

**2. Prefill beats generation for this workload.** An agentic loop re-reads its context every
turn, so prefill is what Claude Code pays per tool result; generation only covers the few
dozen tokens a tool-heavy turn emits. Every challenger beat the incumbent on prefill, by
9–44%, while losing on generation. Gemma4 is 47% slower to generate and 44% faster to read.

**3. Generation speed, for the turns that actually write code.** Still real — a plan or a
long edit is generation-bound — but it is the number people over-weight.

**4. Window size, sharply diminishing, and *allocated ≠ usable*.** North-mini allocates
500,000 tokens in 23.29 GB, and its retrieval is already unreliable at 230k (§8). The window
a model can *hold* and the window it can *attend across* are different numbers. A large
window also costs prefill on every turn — v2 measured Nemotron's 512k as real *and* unusable
at 16 minutes per full-window query. Claude Code compacts context and rarely lives past
250k anyway, and `CLAUDE_CODE_MAX_CONTEXT_TOKENS` must stay **below** the baked window
regardless, because overflowing `num_ctx` does not error — it silently discards to half and
stops tool calling.

> Useful window = min(allocated, **retrieval-verified**, what you can afford to prefill each
> turn). For Claude Code, 262k of verified window beats 500k of nominal window.

**5. Model shape predicts all of the above.** Every MoE measured runs 70–130 tok/s and
finishes the end-to-end task in 42–60 s; every dense model runs 19–31 tok/s and takes
113–179 s, with 4× the KV cost per token (64,784 vs ~16,384 bytes) and therefore *smaller*
usable windows. On a memory-bandwidth-bound box, active parameters per token is the number
that predicts everything else.

**6. Every tag on the box is still a bare tag until you bake one.** All three new models ship
without `num_ctx` (see [`results/inventory-67.txt`](results/inventory-67.txt)) — so as pulled,
not one of them is usable with Claude Code past 16,384 tokens. The good news: **none of them
ships `presence_penalty`**, so v2's single cheapest win (31–35% of throughput) is now fixed
upstream and there is nothing to clear but the window.

## What we got wrong, and corrected

Recorded because the corrections changed the recommendation:

- **"North-mini takes the deep-context slot at 500k"** — **wrong, and retracted mid-project.**
  That was written from allocation plus retrieval verified only to 114k. Deeper testing found
  failures at 230,825 / 398,089 / 456,281 tokens against a reproducible PASS (3/3) at 347,193.
  It gets the deep-context slot **at 262144**, not at its advertised window.
- **A needle FAIL at 320k was first read as a harness artifact** (`done=length`, the model
  still reasoning at token 512). Re-running at `num_predict 2048` reproduced the failure, so
  it is the model, not the budget — the opposite of v1's `num_predict 64` mistake, and it had
  to be checked rather than assumed.
- **North-mini's "256K vs 488K" contradiction was neither.** The GGUF says 500000; Ollama's
  "488K" is 500000/1024 as a display artifact. Cohere's own card understates it.
- **`kv-probe`'s linear fits are not quoted** for north-mini or gemma4: their ladders cross an
  allocation regime (262144 costs *less* than 131072, reproducibly), so a least-squares slope
  through both is meaningless. Cause unproven — no API exposes `num_parallel` and we have no
  shell on `.67`.
- **`kv-probe.sh` defaults to `127.0.0.1:11435`.** Passing `--host` without `--port` sends
  everything to a dead port and fails as a *JSON decode error*, which reads like a broken
  model. Always pass `--port 11434`.

## Reproducing

```shell
./idle.sh        --host 192.168.100.67 --port 11434          # assert the server is empty
./pull-queue.sh                                              # stage B weights
./kv-probe.sh    --host 192.168.100.67 --port 11434 --model <M> --ctxs "..."
./head2head.sh   --host 192.168.100.67 <model>...            # throughput, residency, gates, needle
./needle-v2.sh   --host 192.168.100.67 --port 11434 --model <M> --num-predict 2048 --depths "..."
./cc-session.sh  --host 192.168.100.67 <model>...            # real Claude Code, scored from the repo
```

`.67` is **shared**. `idle.sh` unloads only tags this project owns and waits out anything
else rather than evicting it — `qwen3.6:*` is deliberately treated as foreign, because no
tag-name test can tell a colleague's `claude-ol2` session from our control run.

## Files

| file | what it is |
|---|---|
| `measurements.md` | every measurement, with its method and its caveats |
| `model_cards.md` | one card per model: vendor claim vs measured vs predicted |
| `market_research.md` | the survey — what exists, what fits, what was excluded and why |
| `plan.md` | the plan, its two blockers, and what would invalidate it |
| `results/tokrate.tsv` | throughput rows, machine-readable |
| `results/kv-ladder.tsv` | context ladders |
| `results/cc-session.tsv` | end-to-end session verdicts |
| `results/agentic/*.tsv` | T1–T7 gate results per model |
| `results/inventory-67.txt` | every tag on `.67` with its baked window and capabilities |
| `comparison.md` | the full eight-model comparison, written to be read outside this repo |

## Housekeeping

Ollama tags share weight blobs, so summing `/api/tags` sizes triple-counts: the box held
**215.09 GiB** of real weights, not the 653.51 GiB a naive sum reports. Deleting a redundant
variant frees **zero** bytes; only the last tag referencing a blob returns space.

Removed 2026-08-25 after their measurements were committed — `qwen3.6:27b-mtp-q8_0` ×3,
`laguna-xs-2.1` ×2, `muse-glimmer` ×2, `qwen3.5:9b` ×2 — freeing **69.85 GiB**
(215.09 → 145.24 GiB, 32 → 23 tags). All are re-pullable in ~10 minutes and their numbers
are preserved in `measurements.md` §10–11.
