# Which local model should drive Claude Code? — the 2026-08 field

Measured on **`192.168.100.67`**, 2026-08-25 on Ollama **0.32.9** and 2026-08-27 on Ollama
**0.32.15**. Usable VRAM is **35.56 GB**, not 40.4 — measured twice, a model generation apart
([`measurements.md`](measurements.md) §19c). Server asserted idle before every measurement,
one model resident at a time.

[`measurements.md`](measurements.md) holds every number and how it was taken;
[`model_cards.md`](model_cards.md) is one card per model; [`market_research.md`](market_research.md)
is the survey of what exists; [`plan.md`](plan.md) and [`stage_a_plan.md`](stage_a_plan.md) are
what we set out to do. This is the summary.

> **Read this first: the runtime version is a variable.** `.67` moved from Ollama 0.32.9 to
> 0.32.15 between the two measurement days, and it **re-ranked the field without any model
> changing** (§13). Generation @2k: nemotron **+221%**, north-mini **+60%**, gemma4 **+49%**,
> and the incumbent **0.0%**. The control not moving is what makes this a finding rather than
> noise. Every number below is labelled with the runtime it was taken on.

---

## The verdict

**The incumbent is superseded. Use `north-mini-code-1.0:q4_K_M-ctx256k-agentic` at
`num_ctx 262144`.**

This reverses the 2026-08-25 verdict, and the reason is not that north-mini improved as a
model — it is that 0.32.15 made it 60% faster while leaving `qwen3.6:35b-a3b` exactly where
it was. On the runtime this box now runs, north-mini beats the incumbent on **every axis
measured except vision**:

| | north-mini | incumbent | |
|---|---|---|---|
| generation @2k | **132.9** tok/s | 130.0 | +2% |
| prefill @35k | **4,443** tok/s | 3,996 | +11% |
| resident @262144 | **21.34 GB** | 32.54 GB | **−34%, 11.2 GB freed** |
| deepest verified retrieval | **201,737** | 146,957 | +37% |
| tool gates T1–T7 | 10/10 | 10/10 | tied |
| Claude Code session | 57 s | 58 s | tied |
| vision | no | **yes** | the one loss |

The 11.2 GB is the practical difference: it is the gap between "this box runs one model" and
"this box runs a model with room left over".

| | model | why, in one line |
|---|---|---|
| **default** | `north-mini-code-1.0:q4_K_M-ctx256k-agentic` @ 262144 | fastest-but-one generator, second-best prefill, deepest verified retrieval, 10/10 gates, and 11 GB lighter than the model it replaces |
| **vision** | `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic` @ 262144 | **the fastest prefill measured here** (5,774 tok/s) and the fastest session (54 s), with vision, in 22.15 GB. Prefill is what an agentic loop pays every turn, so this beats the incumbent at the vision job too |
| **deepest window** | `nemotron-3.5-lightning:30b-ctx256k-agentic` | now the **fastest generator on the box** (138.1 tok/s, up from 43.9) and the only model holding 524,288 tokens — but the worst prefill of the four and 34 turns to do a 17-turn job |
| **superseded** | `qwen3.6:35b-a3b-q4_K_M-agentic` | still 10/10 and still has vision, but third on generation, third on prefill, and the heaviest thing on the box at 32.54 GB |
| **measured, not recommended** | `qwen3.8:27b-q4_K_M` @ 131072 | **4.3× slower than the field.** See below |
| **not recommended** | `laguna-xs-2.1` *(deleted)* | the only model that failed a gate. Its 119.5 tok/s is a 0.32.9 number and cannot be re-measured |
| **not recommended** | `muse-glimmer:30b` *(deleted)*, `qwen3.6:27b-q8_0` | dense: 28.5 and 19.5 tok/s on 0.32.9 |

## Qwen3.8: it ran, and the answer is no

The project was commissioned to benchmark it. `.67` was upgraded to Ollama 0.32.15 on
2026-08-27, the registry's HTTP 412 gate cleared, and **Stage A ran in full** — three rungs,
all at 4-bit or better. [`measurements.md`](measurements.md) §12–21.

| rung | window @100% GPU | generation | prefill @35k | gates | session |
|---|---|---|---|---|---|
| `qwen3.8:27b-q4_K_M` | **131,072** | **30.4** tok/s | 1,428 | 9/10 | PASS 111 s |
| `qwen3.8:27b-mtp-q4_K_M` | 131,072 | 36.6 | **767** | — | PASS 109 s |
| `qwen3.8:27b-q8_0` | 65,536 | 19.4 | 1,487 | 8/10 | PASS 137 s |

**It is a good model and the wrong shape for this box.** It drives Claude Code correctly —
fixed the fixture bug with the *identical* tool histogram to the incumbent
(`Bashx4,Readx3,Editx1`), passed T4 and T7 (the two laguna failed), read a screenshot
accurately, and retrieves to 119,015 tokens, which is **90.8% of its window — the best
utilisation ratio in the field.** It is simply 4.3× slower than the models it competes with.

The prediction held exactly. v3 ran `qwen3.6:27b-q4_K_M` as a dense stand-in for the Qwen3.8
it could not pull, and measured **31.0 tok/s**. Qwen3.8's dense 27B measures **30.4**. A
model generation newer, the same shape, the same speed — and its q8 rung landed on its
predecessor's q8 number too (19.41 vs 19.5). **On a memory-bandwidth-bound box, active
parameters per token predicts the outcome, and a new architecture generation does not move
it.**

Two operational notes that cost nothing to act on:

- **Pull `qwen3.8:27b-q4_K_M`, never `qwen3.8:27b`.** The bare tag's params digest is
  byte-identical to the MTP build, so the obvious name silently enables speculative decoding.
  On Qwen3.8 that buys +20% generation for **−46% prefill** — the wrong trade for an agentic
  loop, which re-reads its context every turn (§15b, qualified by §20).
- **Qwen3.8 is not naive-dense.** `full_attention_interval 4` gives it 73,730 B/token of KV
  against 266,240 naive — 3.6× cheaper, and the only reason a dense 27B holds 131k here at
  all (§19b).

## The field on 0.32.15

Re-measured 2026-08-27. **Generation and session wall-clock are 0.32.15 numbers; gates,
residency and needle depth are version-stable** — north-mini's full T1–T7 battery was re-run
on the new runtime and came back byte-identical, including every token count, and residency
was re-checked at 21.34 / 32.54 / 22.15 GB, unchanged.

| | **north-mini-code** | **nemotron-3.5-L** | **incumbent** | **gemma4:26b-a4b** | **qwen3.8:27b** |
|---|---|---|---|---|---|
| vendor | Cohere | NVIDIA | Alibaba | Google DeepMind | Alibaba |
| shape | 30B MoE, 3B active | Mamba-2 + MoE, 3B act. | 36B MoE, 3B active | 26B MoE, 4B active | **dense 27B** |
| **generation** @2k | 132.9 tok/s | **138.1** | 130.0 | 104.1 | 30.4 |
| *…on 0.32.9* | *83.6* | *43.9* | *130.0* | *70.0* | *n/a* |
| **prefill** @35k | 4,443 | 2,797 | 3,996 | **5,774** | 1,428 |
| resident @262144 | **21.34 GB** | 31.21 GB | 32.54 GB | 22.15 GB | 26.24 GB @131072 |
| max window @100% GPU | 262144 *(usable)* | **524,288** | 262144 | 262144 | 131,072 |
| **tool gates T1–T7** | **10/10** | **10/10** | **10/10** | **10/10** | 9/10 |
| needle, deepest verified | **201,737** | 161,516 | 146,957 | 143,324 | 119,015 |
| *…as % of its window* | 40% | 31% | 56% | 55% | **90.8%** |
| Claude Code session | 57 s | 72 s | 58 s | **54 s** | 111 s |
| vision | no | no | **yes** | **yes** | **yes** |

**The top four are now tied end to end: 54–58 s.** The incumbent's session moved 46 s → 58 s
while its throughput did not move at all, which is the clearest available evidence that this
metric carries real run-to-run variance and that a 4-second gap between models means nothing.
Nemotron's 72 s is outside that band, and the transcript says why: **34 turns to do a job the
others did in 16–19.** Speed per token is not the same as economy of turns.

Qwen3.8's 111 s is not in the band at all, and its 9/10 is the only non-perfect gate score
among the models still recommended for anything.

### Models measured only on 0.32.9

`laguna-xs-2.1` (119.5 tok/s, **8/10 gates** — the only gate failure in the project),
`muse-glimmer:30b` (28.5) and `qwen3.6:27b-q8_0` (19.5) were deleted in §11 before the
upgrade. **Their speed numbers cannot be compared to the table above** and should not be
ranked against it — given that three of four re-measured models moved by 49–221%, an
un-remeasured number is not a slower result, it is an unknown one. Their gate results stand,
because gates proved version-stable.

The dense stand-in `qwen3.6:27b-q4_K_M` (31.0 tok/s on 0.32.9) has served its purpose: it
predicted Qwen3.8's 30.4 to within 2%.

## What actually matters, in order

The measurements disagree with the intuition that a bigger window and a bigger tok/s number
are what to shop for.

**0. The runtime version, which was not on this list before 2026-08-27.** Upgrading Ollama
0.32.9 → 0.32.15 changed generation throughput by **0% to +221% depending on the model** and
re-ranked the field, with no model changing. It is now the first thing to pin when comparing
two numbers, and the reason every table here carries a version. A benchmark without a runtime
version on it is not a result.

**1. Tool-call reliability, and it is not close.** It is the only property that is pass/fail
rather than a gradient. Laguna is the fastest challenger and is not recommended, because it
serialises parallel tool calls (T4) and dropped one call in three at 53,145 tokens (T7).
A model that is 9% faster and breaks the loop on turn three is a worse tool, not a faster
one — and **neither failure appears in any throughput benchmark.**

**2. Prefill beats generation for this workload.** An agentic loop re-reads its context every
turn, so prefill is what Claude Code pays per tool result; generation only covers the few
dozen tokens a tool-heavy turn emits. On 0.32.15 gemma4 is **20% slower to generate and
44% faster to read** than the incumbent, which is why it takes the vision slot from it. The
sharpest case is Qwen3.8's MTP head: **+20% generation for −46% prefill**, which is a net
loss on a large prompt (§15b) and a wash on a small one (§20).

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

**5. Model shape predicts all of the above, and Qwen3.8 is the confirmation.** On 0.32.15
every MoE runs 104–138 tok/s and finishes the task in 54–72 s; every dense model runs
19–30 tok/s and takes 111–137 s. Ten models deep, no exception. The strongest form of the
claim: v3 measured a dense stand-in at **31.0 tok/s** as a proxy for a Qwen3.8 it could not
pull, and when Qwen3.8 finally ran it measured **30.4** — a model generation newer, the same
shape, the same speed, and the same again at the q8 rung (19.41 vs 19.5). **On a
memory-bandwidth-bound box, active parameters per token predicts the outcome and an
architecture generation does not move it.**

Dense also costs window: Qwen3.8 pays **73,730 B/token** of KV against the incumbent's
~16,384, which is why it holds 131,072 where the MoEs hold 262,144.

**6. Every model here is unusable as pulled until you bake a window.** Every base tag ships
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
- **The 2026-08-25 verdict was right for its runtime and wrong for this one.** "Keep the
  incumbent, nothing displaced it" was published on 0.32.9 and did not survive an Ollama
  upgrade. The failure was not the measurement, it was assuming the runtime was a constant —
  now item 0 above. `plan.md` §2 C1 had flagged the risk in advance, which is the only reason
  a control was re-measured before any Stage A number was taken.
- **"Qwen3.8 is a dense 27B, so its KV will be huge"** — half wrong. It is dense in parameter
  count but `full_attention_interval 4` makes only 18 of 65 layers hold full KV, so it costs
  73,730 B/token rather than the naive 266,240 (§19b). Without that it could not have held
  131k on this box at all. The speed prediction was right; the memory prediction was not.
- **`kv-probe.sh`'s least-squares slope is the wrong estimator, and this was quoted once
  before it was caught.** §14a first recorded 69,131 B/token from the fit. The fit averages
  across rungs that spill and rungs that have not amortised a fixed overhead. Marginal cost
  between two adjacent rungs that both sit at 100% GPU gives **73,730 B/token, reproduced to
  the byte three times across two quantizations** (§19b) — and that number recovers both
  manifests' weights to within 0.4%, which the fit does not.
- **q8's T5 PARTIAL looked like "higher precision, worse tool caller".** It is not. Re-run
  n=11 per rung: q4 11/11, q8 9/11, Fisher p ≈ 0.48 (§19f). What it did expose is that the
  gate battery runs at the shipped **temperature 1**, so every single-shot T1–T5 result in
  this repo can flip on a re-run. T7 samples 3× and is the more trustworthy gate.
- **MTP was called a net loss from one row.** True at 35k tokens (28.9 s vs 50.9 s), but the
  end-to-end session is 109 s vs 111 s — indistinguishable, because the fixture's prompts are
  short (§20). The recommendation stands for large contexts; the blanket phrasing did not.
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
./pull-queue.sh                                              # stage A weights (qwen3.8)
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
| `stage_a_plan.md` | the Qwen3.8 run: the cleared blocker, the fit budget, the pre-registered "no" conditions |
| `results/tokrate.tsv` | throughput rows, machine-readable |
| `results/kv-ladder.tsv` | context ladders |
| `results/cc-session.tsv` | end-to-end session verdicts |
| `results/agentic/*.tsv` | T1–T7 gate results, per model |
| `results/show-qwen38.txt` | raw `/api/show` for both Qwen3.8 q4 tags |
| `results/cc-session-0.32.9.tsv` | the pre-upgrade session table, kept so the version delta is auditable |
| `../ollamaClaudeCode_v2/results/` | raw data for nemotron, muse-glimmer and 27b-q8_0, quoted here but not duplicated — see `measurements.md` §10 |
| `results/inventory-67.txt` | every tag on `.67` with its baked window and capabilities |
| `comparison.md` | the full model comparison, written to be read outside this repo |

## Housekeeping

Ollama tags share weight blobs, so summing `/api/tags` sizes triple-counts: the box held
**215.09 GiB** of real weights, not the 653.51 GiB a naive sum reports. Deleting a redundant
variant frees **zero** bytes; only the last tag referencing a blob returns space.

Stage A added six tags on 2026-08-27 (**24 total**): `qwen3.8:27b-q4_K_M`, `-mtp-q4_K_M` and
`-q8_0`, plus a baked `-agentic` variant of each. The two q4 tags **share one weight blob**,
so the pair costs 16.52 GiB, not 33 — the MTP tag pulled in **1 second**. Real added weight
on disk: 16.52 + 27.92 = **44.44 GiB**.

Removed 2026-08-25 after their measurements were committed — `qwen3.6:27b-mtp-q8_0` ×3,
`laguna-xs-2.1` ×2, `muse-glimmer` ×2, `qwen3.5:9b` ×2 — freeing **69.85 GiB**
(215.09 → 145.24 GiB, 32 → 23 tags). All are re-pullable in ~10 minutes and their numbers
are preserved in `measurements.md` §10–11.
