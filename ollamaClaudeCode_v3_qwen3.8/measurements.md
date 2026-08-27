# v3 measurements

Everything measured on `192.168.100.67`, Ollama **0.32.9**, ≈35.5 GB usable, server asserted
idle before every stage. Raw data in `results/`. Written as the runs land, so it grows from
the top down; the verdict lives in `README.md`.

Named `measurements.md` rather than `qwen38_eval.md` as `plan.md` originally proposed,
because as of 2026-08-25 it contains **no Qwen3.8 data** — that stage is blocked on the
0.32.15 upgrade, and a filename claiming otherwise would be the kind of quiet
mislabelling this project exists to avoid.

---

## 1. Context ladders — how much window this box actually holds

`./kv-probe.sh --host 192.168.100.67 --port 11434 --model <M> --ctxs "..."`, one model
resident at a time. Raw: `results/kv-ladder.tsv`.

| num_ctx | laguna-xs-2.1 | north-mini-code-1.0 | gemma4:26b-a4b |
|---|---|---|---|
| 32,768 | 21.25 GB | 20.04 GB | 18.39 GB |
| 131,072 | 22.86 GB | 21.65 GB | 22.90 GB |
| 262,144 | **25.01 GB** | 21.34 GB | 22.15 GB |
| 393,216 | — | 22.41 GB | — |
| 500,000 | — | **23.29 GB** | — |

**Every entry is 100% GPU-resident.** Not one of the three needed a reduced window to stay
off the CPU, which is a real change from v2's field — there, the dense q8 was capped at
`num_ctx 81920` and only Nemotron went past 262144, at 31.21 GB.

### 1a. North-mini holds 500,000 tokens in 23.29 GB

The headline number of this stage. Its full native window — the one the GGUF declares and
Cohere's own card understates as 256K — fits with **~12 GB of headroom** on a box where v2
could not fit a dense 27B q8 at 131072.

For scale, against the deep-context option v2 recommended for exactly this job:

| | `nemotron-3.5-lightning` (v2) | `north-mini-code-1.0` (v3) |
|---|---|---|
| largest window at 100% GPU | 524,288 | 500,000 |
| resident at 262,144 | 31.21 GB | **21.34 GB** |
| vision | no | no |

Nemotron's window is nominally larger, but v2 measured the cost of using it: **16 minutes**
for a single full-window query, ~380 s of that just allocating the KV cache at load. Whether
North-mini's cheaper allocation translates into a usable full-window turn is a throughput
question, not a memory one, and §2 answers it.

### 1b. Two ladders run backwards, and the fits must not be quoted

North-mini and Gemma4 both cost **less** at 262,144 than at 131,072 — 21.65 → 21.34 GB and
22.90 → 22.15 GB. A larger window using less memory is not a rounding artefact; the numbers
reproduced to within 10 MB across two independent runs an hour apart.

The window itself is not being silently reduced. Re-probed directly, `/api/ps` reports
`context_length` **exactly equal to the requested `num_ctx`** in every case, 131072 and
262144 alike, and 500000 for north-mini. So this is not v2's truncation cliff wearing a new
hat.

**Hypothesis, stated as one:** Ollama sizes the KV cache as `num_parallel × num_ctx` and
chooses `num_parallel` dynamically from available memory, so the slot count drops from 2 to
1 as the per-slot window grows and total allocation falls. That would fit all three shapes,
including Laguna's monotonic rise — its 16 KB/token is heavy enough that it is presumably
already on one slot throughout.

**It is not proven.** No Ollama API exposes `num_parallel`, we have no shell on `.67` and
therefore no server log, and every test that would settle it needs one of those. It is
recorded because the consequence is concrete:

> **`kv-probe.sh`'s printed linear fit is unsafe on these models.** It assumes one
> allocation regime and least-squares straight through two. Laguna's 16,384 B/token is
> clean because that ladder is monotonic; the 5,233 B/token quoted for north-mini and
> 15,190 for gemma4 are artefacts of a regime change and **are not quoted anywhere in this
> report**.

The functional question — does the model *retrieve* across the window it was given — is not
answerable from allocation bytes at all, and is settled by the needle test instead.

### 1c. The baked variants

None of the three ships `presence_penalty` and none has an MTP draft head, so unlike v2's
`-agentic` variants there was nothing to clear. **The only override is `num_ctx`** — stated
plainly so the variants are not credited with more than they do:

| variant | from | `num_ctx` | resident |
|---|---|---|---|
| `laguna-xs-2.1:q4_K_M-ctx256k-agentic` | `laguna-xs-2.1:q4_K_M` | 262144 | 25.01 GB |
| `north-mini-code-1.0:q4_K_M-ctx500k-agentic` | `north-mini-code-1.0:q4_K_M` | 500000 | 23.29 GB |
| `north-mini-code-1.0:q4_K_M-ctx256k-agentic` | `north-mini-code-1.0:q4_K_M` | 262144 | 21.34 GB |
| `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic` | `gemma4:26b-a4b-it-q4_K_M` | 262144 | 22.15 GB |

The 262144 north-mini variant exists so all three models are compared at the *same* window;
the 500000 one is what it would actually be deployed at.

---

## 2. Throughput — nobody beats the incumbent on generation, everybody beats it on prefill

`./tokrate.sh`, temperature 0, fixed `num_predict`, Ollama's own counters. Raw:
`results/tokrate.tsv`. The incumbent row is v2's, taken on the same Ollama 0.32.9 — a
same-session re-measurement is in §5.

| model | gen @2k words | gen @20k words | **prefill @20k words** | cold load |
|---|---|---|---|---|
| `qwen3.6:35b-a3b` *(incumbent, v2)* | **131.4** | **112.3** | 3,988 | 11.6 s |
| `laguna-xs-2.1` | 119.5 | 93.5 | 4,882 | 10.6 s |
| `north-mini-code-1.0` | 83.6 | 78.2 | 4,331 | 11.5 s |
| `gemma4:26b-a4b` | 70.0 | 65.4 | **5,740** | 14.4 s |

Two readings, and they point different ways:

**On generation the incumbent still wins.** Laguna gets closest at 119.5 (9% behind);
North-mini is 36% behind and Gemma4 47%. Nothing in the 2026-08 field displaces
`qwen3.6:35b-a3b` on raw token output.

**On prefill all three beat it** — Gemma4 by 44%, Laguna by 22%, North-mini by 9%. This is
not a footnote. An agentic loop re-reads its context every turn, so prefill is what Claude
Code actually pays on each tool result; generation is only paid for the tokens the model
emits, which in a tool-heavy turn is a few dozen.

### 2a. Tokenisers are not comparable, and v2 was caught by this once

The same 20,000-word prompt tokenises differently per model, so tok/s is not a
like-for-like rate:

| model | tokens per word | gen @2k in **words/s** |
|---|---|---|
| `qwen3.6:35b-a3b` | 1.755 | **74.9** |
| `laguna-xs-2.1` | 1.711 | 69.9 |
| `north-mini-code-1.0` | **1.358** | 61.5 |
| `gemma4:26b-a4b` | 1.710 | 40.9 |

North-mini's tokeniser is **21% more efficient** than the others'. That does not close the
generation gap — it narrows 36% to 18% — but it compounds elsewhere: its 500,000-token
window holds appreciably more *source code* than 500,000 tokens of Laguna's would, and its
needle depths in §4 look shallower than the others' for exactly this reason rather than
through worse retrieval. v2 made the mirror-image error with Nemotron and had to correct it.

**Stated as an assumption, not a measurement:** the words/s column applies the *prompt*
tokenisation ratio to *generation*, which assumes output tokenises like input. Close enough
to rank with, not precise enough to quote to three figures.

## 3. Tool gates — the fastest challenger is the least reliable

v1's `agentic-test.sh`, T1–T7 against `/v1/messages`. Raw: `results/agentic/*.tsv`.

| gate | laguna | north-mini | gemma4 |
|---|---|---|---|
| T1 single tool | PASS | PASS | PASS |
| T2 tool selection | PASS | PASS | PASS |
| T3 multi-turn tool_result | PASS | PASS | PASS |
| T4 **parallel tool calls** | **PARTIAL** — 1 call only | PASS — 2 calls | PASS — 2 calls |
| T5 complex nested schema | PASS | PASS | PASS |
| T6 needle 4k/16k/60k/120k | PASS ×4 | PASS ×4 | PASS ×4 |
| T7 **tool call at long context** | **FLAKY** — 2/3 at 53,145 tok | PASS — 3/3 at 43,300 | PASS — 3/3 at 55,535 |
| | **8/10** | **10/10** | **10/10** |

This is the result that reorders the field. **Laguna is the fastest challenger and the only
one that fails a gate** — twice, and both failures land exactly where Claude Code lives:

- **T4** — it emits one tool call where two independent ones were available. Claude Code
  batches independent calls into a single turn by design; a model that serialises them pays
  a full round trip per call, which eats the prefill advantage §2 just credited it with.
- **T7** — tool calling at 53k tokens succeeded twice and failed once. A flaky gate is worse
  than a failed one for an agent loop: it fails on the third turn of a long session rather
  than on the first, after the context is expensive to rebuild.

Neither is a throughput problem, and neither would appear in any speed benchmark.

## 4. Needle retrieval — all three, clean

`./needle-v2.sh`, same document for every model, `num_predict 512`, baked `num_ctx 262144`.
Raw: `results/needle-v2.log`.

| depth | laguna | north-mini | gemma4 |
|---|---|---|---|
| 5k | PASS @ 4,321 tok | PASS @ 3,533 | PASS @ 4,292 |
| 21k | PASS @ 17,407 | PASS @ 13,711 | PASS @ 17,378 |
| 80k | PASS @ 70,633 | PASS @ 56,281 | PASS @ 70,604 |
| 160k | **PASS @ 143,353** | **PASS @ 114,457** | **PASS @ 143,324** |

Every model returned the exact passphrase with `done_reason=stop`. North-mini's lower token
counts at identical depths are the tokeniser of §2a, not weaker retrieval — the document is
byte-identical.

**These are the four standard depths only.** North-mini was later pushed much further (§8) and
retrieves reliably to **201,737 tokens**; the 114,457 in this row is where the 160k-word
document lands in *its* tokeniser, not a ceiling. The other three were not re-tested past
160k.

Worth naming: **Laguna passes at 143k despite its 262144 window being YaRN-extended from a
native 8192** (`rope.scaling.factor = 32`). That was the specific risk flagged in its model
card, and it did not materialise at this depth.

Not tested: retrieval beyond 160k, and North-mini at its full 500,000. Both are open.

## 5. Control re-measurement — v2 reproduces to within 2%

`qwen3.6:35b-a3b-q4_K_M-agentic`, re-run 2026-08-25 in the same session as the challengers,
still on Ollama 0.32.9. The point is to know whether v2's numbers can be compared against
v3's at all.

| | v2 (2026-08-13) | v3 (2026-08-25) | drift |
|---|---|---|---|
| gen @2k words | 131.37 | 130.04 | −1.0% |
| gen @20k words | 112.32 | 112.15 | −0.2% |
| prefill @20k words | 3,987.9 | 3,911.1 | −1.9% |
| resident @262144 | 32.54 GB | 32.54 GB | none |
| tool gates | 10/10 | 10/10 | none |
| needle @160k | PASS @ 146,957 tok | PASS @ **146,957** tok | none |

Twelve days apart, on a shared box, the deepest needle reproduced to the *token* and
throughput drifted under 2%. So the v2 figures quoted throughout this document are sound
comparators **for as long as `.67` stays on 0.32.9**, and the §2 table's mixing of v2 and v3
rows is safe.

That guarantee expires the moment the box is upgraded for Qwen3.8 — 0.32.15's notes claim
metadata caching that halves time-to-first-token, which would land directly on the prefill
column and silently flatter everything measured after it. The control gets run a third time
then, which is why `plan.md` §6 treats an upgrade landing mid-run as a reason to discard and
re-measure rather than to carry on.

---

## 6. Where this leaves the field, before the end-to-end runs

| | incumbent | laguna | north-mini | gemma4 |
|---|---|---|---|---|
| gen @2k | **130.0** | 119.5 | 83.6 | 70.0 |
| prefill @35k | 3,911 | 4,882 | 4,331 | **5,740** |
| gates | **10/10** | 8/10 | **10/10** | **10/10** |
| max window @100% GPU | 262,144 | 262,144 | **500,000** | 262,144 |
| resident at that window | 32.54 GB | 25.01 GB | **23.29 GB** | 22.15 GB |
| vision | yes | no | no | yes |

Nothing here displaces the incumbent as the default driver: it is fastest at generation,
clean on every gate, and retrieves deepest. What has changed is the **deep-context** slot,
which v2 gave to Nemotron at 44.9 tok/s and 31.21 GB. North-mini holds a comparable window
for 8 GB less, passes every gate, and generates **1.9× faster** — and that is before its 21%
tokeniser advantage.

> **Corrected in §8.** The sentence above originally continued "…which makes its 500,000
> tokens hold more real source than Nemotron's 524,288", and recommended north-mini *at its
> 500,000 window*. That was written from allocation plus retrieval verified only to 114,457
> tokens, and §8 shows it does not hold. North-mini keeps the deep-context slot, **at
> 262144**. The claim is left visible rather than edited away, because the correction is the
> useful part.

§7 is the test that can still overturn this: none of the above proves any of them can finish
a change in a real repository.


## 7. End-to-end Claude Code sessions — all four pass, and that is the finding

`./cc-session.sh`, real `claude -p` against a fixture repository whose `median()` returns
the upper middle value instead of the mean of the two. Scored from the repository
afterwards, not from the model's summary. Raw: `results/cc-session.tsv`,
`results/cc-*.jsonl`.

| model | verdict | wall | turns | tools |
|---|---|---|---|---|
| `qwen3.6:35b-a3b` *(incumbent)* | **PASS** | 46 s | 16 | Bash×4, Read×3, Edit×1 |
| `laguna-xs-2.1` | **PASS** | 42 s | 18 | Bash×4, Read×2, Edit×1 |
| `north-mini-code-1.0` | **PASS** | 60 s | 22 | Read×5, Bash×5, Edit×1 |
| `gemma4:26b-a4b` | **PASS** | 60 s | 16 | Bash×3, Read×2, Edit×2 |

No `CHEAT`, no `FAIL`. Every one read the failing test, edited `stats.py` only, and re-ran
pytest to confirm. The diffs were inspected by hand rather than taken on trust, and all four
are correct and idiomatic — each independently produced the even/odd branch, one of them
with explanatory comments:

```python
-    return ordered[len(ordered) // 2]
+    mid = len(ordered) // 2
+    if len(ordered) % 2 == 0:
+        return (ordered[mid - 1] + ordered[mid]) / 2
+    return ordered[mid]
```

Every model also reached for the right tools in the right order — Read before Edit, Bash to
run the suite — and none of them blind-wrote the file with Write, which was the specific
behaviour this test was built to catch.

**The honest reading: this task does not discriminate.** Four models spanning 70 to 130
tok/s and 8/10 to 10/10 on the gates all cleared it inside a minute. That is worth knowing —
every candidate in the 2026-08 field can drive Claude Code through a real single-file
change, which was not a given — but it means **the gates in §3, not this test, are what
separate them.** Laguna's T4 and T7 failures did not surface here because a one-file fix
never needs two parallel tool calls and never reaches 53k tokens of context.

A test that *would* discriminate needs the conditions Laguna actually failed under: several
independent files to read in one turn, and a context deep enough to be in T7 territory
before the first edit. That is not built, and until it is, **no claim is made here about
these models on repository-scale work.** What is claimed is narrow and measured: on a
single-file fix, all four work.

---

## 8. How deep does North-mini actually retrieve? — not as deep as it allocates

§1 established that it *allocates* 500,000 tokens in 23.29 GB. That is a memory result, and
a memory result cannot tell you whether the model attends across the window. This is the
retrieval test, same document, needle at the midpoint in every case.

| prompt tokens | baked window | request `num_ctx` | `num_predict` | runs | result |
|---|---|---|---|---|---|
| 114,457 | 262144 | 262144 | 512 | 1 | **PASS** |
| **172,649** | 262144 | 262144 | 2048 | 1 | **PASS** — `eval=13` |
| **201,737** | 262144 | 262144 | 2048 | 1 | **PASS** — `eval=13` |
| **230,825** | 500000 | 392192 | 512 | 1 | FAIL — `done=length` |
| **230,825** | 500000 | 392192 | 2048 | 1 | FAIL — `done=length` |
| **230,825** | 500000 | **500000** | 2048 | 1 | FAIL — `done=length` |
| **230,825** | **262144** | 262144 | 2048 | 1 | FAIL — `done=length` |
| **230,825** | 262144 | 262144 | 4096, `think:true` | 1 | FAIL — `done=stop`, `eval=823` |
| **347,193** | 500000 | 500000 | 512 | 1 | **PASS** — `done=stop`, `eval=13` |
| **347,193** | 500000 | 500000 | 2048 | 2 | **PASS** ×2 — identical, `eval=13` |
| 398,089 | 500000 | 500000 | 2048 | 1 | FAIL — `done=stop`, restates the question |
| 456,281 | 500000 | 500000 | 512 | 1 | FAIL — `done=stop`, "the document does not contain…" |

**Reliable retrieval reaches 201,737 tokens.** The 114,457 figure first published here was
simply the deepest point tested at the time, not a ceiling; bisecting upward found clean
passes at 172,649 and 201,737, each answering in 13 tokens.

**The result is still non-monotonic and reproducible in both directions.** 230,825 tokens now
fails **five times out of five**; 347,193 — deeper — passes three times out of three. That is
not a ceiling with noise around it.

Four explanations were tested and all four are dead:

- **Harness budget.** The first 230k failure was `done=length` with the model still
  reasoning, which looks exactly like v1's `num_predict 64` mistake. Re-run at 2048: same
  failure, 2048 tokens of restating the prompt without answering. **Not the budget.**
- **Harness window sizing.** needle-v2 sizes each request's `num_ctx` from the word count
  (`min(w*2.4+8192, baked)`), so the 230k runs got 392192 while the passing 347k runs got
  500000 — and v2 established that overflowing `num_ctx` silently halves it. Re-sent the
  identical document with `num_ctx` pinned to 500000: **same failure.** Not the sizing either.
- **The baked window itself.** Every failure so far had been on the `-ctx500k` variant and the
  one pass on `-ctx256k`, so the 500,000-token bake was a live suspect — it would have meant
  the model degrades at *every* depth when built with an oversized window. 230,825 tokens fits
  inside 262,144, so the identical document was sent to the **`-ctx256k`** variant:
  **same failure.** The baked window is not the variable; depth is.
- **Leaked reasoning rather than lost retrieval.** Every failure begins
  `'The user asks: "Answer only the question…'` and either loops to the cap or stops after
  restating — the signature of reasoning text arriving in `content`, and v2 found Ollama does
  not honour `think:false` on every family. Re-sent with **`think:true`** and a 4096-token
  budget: `thinking` came back **empty**, `content` held 4,247 characters of reasoning-style
  prose, and **the passphrase appears in neither**. Not a thinking-mode artifact — the model
  genuinely does not retrieve at this depth.

So it is the model, and **we cannot explain it.** What can be said is what was observed: at
230,825 tokens North-mini reliably restates the question and rambles instead of answering,
and at 347,193 it reliably answers instantly. Five failures and three passes, across two
baked windows, three request windows, three generation budgets and both thinking modes.

### 8a. The failure mode is the good one, at least

At 456,281 tokens it answered *"The document does not contain any information about a deploy…"*
— it reported not finding the needle. Compare v2's worst-in-class result: Nemotron, truncated,
**invented a plausible passphrase** (`deploy-passphrase-2024`) with no error and no signal.
For an agent that acts on what it reads, an honest "not found" and a confident fabrication are
not the same class of failure.

### 8b. What this changes

**Deploy North-mini at `num_ctx 262144`, not 500000.** Its 262144 variant is 21.34 GB, passes
10/10 gates and retrieves cleanly to **201,737 tokens** — and at that window it is still a
straight upgrade on the deep-context slot v2 gave to Nemotron: 8 GB lighter, 1.9× faster,
same gate score.

**The practical ceiling is ~200k tokens, and that is comfortably more than Claude Code will
ask of it.** `CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000` in the alias sits just under the
measured limit, which is the right side of it by construction rather than by luck.

The 500000 variant stays on the box for anyone who wants to probe further, but it is not a
recommendation. **Still not explained:** why 230,825 fails while 347,193 passes. Five
attempts at the failing depth and three at the passing one, with every environmental
variable we can reach held constant or varied deliberately, leave the inversion intact.

---

## 9. The dense 27B — a measured proxy for the Qwen3.8 we cannot run

Qwen3.8 is blocked (§ `market_research.md` 1) and it is **dense**. `qwen3.6:27b-q4_K_M` is
the same vendor, the same 27B dense shape and the same quantisation as
`qwen3.8:27b-q4_K_M` — so measuring it converts "is a dense 27B fast enough here?" from
speculation into a number.

It had never been measured cleanly: v1's run spilled to CPU (`9.60/17.37 SPLIT`) and its
numbers are unusable, and the `-ctx128k` tag on the box bakes `presence_penalty 1.5` — the
vendor default worth 31–35%. A clean variant was baked for this:
`qwen3.6:27b-q4_K_M-ctx128k-agentic`, `num_ctx 131072`, `presence_penalty 0`.

### 9a. Dense KV is 4× heavier per token, and it changes the window

| num_ctx | resident | GPU |
|---|---|---|
| 32,768 | 19.29 GB | 100% |
| 81,920 | 25.34 GB | 100% |
| 131,072 | **30.17 GB** | **100%** |
| 262,144 | 34.97 GB | **96%** — 1.28 GB in system RAM |

`fit: total_bytes = 19.21 GB + **64,784** × num_ctx`

Against the MoE field, that slope is the whole story:

| model | bytes per token of KV |
|---|---|
| `qwen3.6:27b-q4_K_M` **(dense)** | **64,784** |
| `laguna-xs-2.1` (MoE) | 16,384 |

**4.0× the KV cost per token**, because a dense model has no sparse attention layout to
exploit — and v2 measured a 12.5% spill at **5.3× slower**, so the 96% row is not a near-miss,
it is a cliff.

### 9b. What this predicts for Qwen3.8, stated as a prediction

`qwen3.8:27b-q4_K_M` is 27.3B dense at Q4_K_M, essentially this model's shape with 17.74 GB
of weights against this one's 17.42 GB. If its KV layout is comparable — the same family
string `qwen35` appears in both manifests — then:

> **Qwen3.8's advertised 256K window will not fit at 100% GPU on this box.** The dense
> ceiling measured here is **131,072**, and 262,144 spills. Expect to bake Qwen3.8 at
> 131072, not at its native 262144.

This is an extrapolation from one model to another, not a measurement of Qwen3.8. It is
recorded so that Stage A has a falsifiable prediction to check rather than a blank page.

---

## 10. The dense proxy and the v2 models, measured end to end

The field was widened to eight so that "dense vs MoE" is a measured contrast rather than an
assertion. Throughput, gates and needle for `nemotron-3.5-lightning`, `muse-glimmer` and
`qwen3.6:27b-q8_0` are v2's, taken on this same Ollama 0.32.9 and left untouched (§5 shows
that runtime reproduces to within 2%). What did not exist for any of them — and now does — is
an **end-to-end Claude Code session**.

**Where their raw data lives.** This directory's `results/` holds only what v3 measured. The
three carried-over models' rows are in v2 and were not copied, so that there is exactly one
copy of each measurement:

| model | throughput | gates | needle |
|---|---|---|---|
| `nemotron-3.5-lightning` | `../ollamaClaudeCode_v2/results/tokrate.tsv` | `../ollamaClaudeCode_v2/results/agentic/nemotron-3.5-lightning_30b-ctx256k-agentic.tsv` | `../ollamaClaudeCode_v2/results/needle-v2.log` |
| `muse-glimmer` | same file | `…/agentic/muse-glimmer_30b-ctx128k-agentic.tsv` | same file |
| `qwen3.6:27b-q8_0` | same file | `…/agentic/qwen3.6_27b-q8_0-agentic.tsv` | same file |

Their **cc-session** rows are v3's own, in `results/cc-session.tsv` — that gate did not exist
in v2.

### 10a. Dense 27B q4 — the Qwen3.8 proxy, full battery

| | value |
|---|---|
| generation @0 / @2k / @20k words | 31.20 / 31.04 / 27.84 tok/s |
| prefill @2k / @20k words | 873.5 / 1,307.3 tok/s |
| max window @100% GPU | **131,072** (262,144 spills to 96%) |
| resident there | 30.17 GB |
| tool gates | **9/10** |
| needle | PASS to 72,419; **FAIL at 160k** |
| Claude Code session | **PASS, 140 s**, 16 turns |

The one gate failure is a *window* failure, not a capability failure — and its shape is the
important part. At the 160k depth the needle harness sent a document larger than 131,072
tokens; `prompt_eval` came back as **65,538**, exactly half the baked window, and the model
answered `'standard policy'` — a fragment of the filler text. No error, no refusal. That is
v2's silent-halving cliff reproduced on a third model, and it fabricates rather than fails.

`qwen3.6:27b-q8_0` behaves identically one rung down: `prompt_eval=40962` against an 81,920
window, answering `'5276'`.

### 10b. End-to-end sessions, all eight

| model | shape | verdict | wall | turns |
|---|---|---|---|---|
| laguna-xs-2.1 | MoE-3B | PASS | **42 s** | 18 |
| qwen3.6:35b-a3b | MoE-3B | PASS | 46 s | 16 |
| north-mini-code-1.0 | MoE-3B | PASS | 60 s | 22 |
| gemma4:26b-a4b | MoE-4B | PASS | 60 s | 16 |
| nemotron-3.5-lightning | Mamba-2+MoE | PASS | 113 s | 24 |
| qwen3.6:27b-q4 | **dense** | PASS | 140 s | 16 |
| muse-glimmer:30b | **dense** | PASS | 160 s | 20 |
| qwen3.6:27b-q8 | **dense** | PASS | 179 s | 15 |

**All eight pass, and the null result from §7 now has a shape.** With four models the session
test looked like it discriminated on nothing. With eight it discriminates cleanly on
*architecture*: every MoE finishes in 42–60 s, every dense or hybrid model in 113–179 s —
**4.3× between fastest and slowest for identical work**. Capability is flat; throughput is
not, and on a real workload that gap is the entire difference.

Turn counts do not track wall clock (15 turns for the slowest, 18 for the fastest), which is
the expected result: the models differ in how fast they emit tokens, not in how many steps
they need.

### 10c. Muse Glimmer's gate score needs an asterisk

`agentic-test.sh` reports T6 FAIL at 4k/16k/60k for Muse. Those are v1's `num_predict 64`
artifact, not retrieval failures — Muse needs ~70 tokens to emit the passphrase, and the raw
log shows it using `eval=70–84`. Re-run under `needle-v2.sh` with a 512-token budget it passes
**all four depths, deepest 114,487 tokens**. Scoring it from the raw rows would put 6/10 next
to other models' 10/10 and misrepresent it, so this report scores it 10/10 with the asterisk
visible.

---

## 11. Housekeeping — the tag sum lies, and what was deleted

**Ollama tags share weight blobs.** `qwen3.6:35b-a3b-q4_K_M` and its five variants are one
22.29 GiB blob with six manifests pointing at it. Summing `/api/tags` sizes therefore
counts that blob six times:

```
sum of all tag sizes :  653.51 GiB   <- what a naive jq sum reports
unique weight blobs  :  215.09 GiB   <- real disk
double-counted       :  438.42 GiB
```

The operational consequence: **deleting a redundant variant frees exactly zero bytes.** Space
returns only when the last tag referencing a blob goes.

Deleted 2026-08-25, after every measurement was taken and committed:

| removed | tags | freed |
|---|---|---|
| `qwen3.6:27b-mtp-q8_0` + `-ctx128k` + `-ctx60k` | 3 | 27.92 GiB |
| `laguna-xs-2.1:q4_K_M` + `-ctx256k-agentic` | 2 | 18.88 GiB |
| `muse-glimmer:30b` + `-ctx128k-agentic` | 2 | 16.91 GiB |
| `qwen3.5:9b` + `-ctx80k` | 2 | 6.14 GiB |
| **total** | **9** | **69.85 GiB** |

Verified by measuring unique-blob totals before and after: **215.09 → 145.24 GiB**, 32 → 23
tags. Every deleted model is re-pullable in ~10 minutes at the 32 MB/s this box gets, and
their measurements are preserved above.

**Kept by explicit decision:** the whole `nemotron-3.5-lightning` family; every non-MTP
`qwen3.6` tag; and `qwen3.6:35b-a3b-mtp-q4_K_M`, which v2 measured at 129 tok/s and 28.89 GB
resident — 3.65 GB lighter than the incumbent and still the best speed-per-GB on the box.

### 11a. Second pass — project-created tags, 2026-08-25

A follow-up pass removed five more tags, all created by this project and none of them needed:
`qwen3.6:35b-a3b-q4_K_M-isot0` and `-isopp0` (v2's finished sampling ablations),
`north-mini-code-1.0:q4_K_M-ctx500k-agentic` (§8 says do not deploy it) and the bare
`north-mini-code-1.0:q4_K_M` and `gemma4:26b-a4b-it-q4_K_M` tags pulled by v3.

**It freed 0.00 GiB, exactly as predicted** — every one shares a blob with a tag being kept.
That is the §11 rule demonstrated rather than asserted: 23 → 18 tags, 145.24 GiB unchanged.

**Deliberately left alone: everything that predates v2/v3.** Twelve of the eighteen remaining
tags are pre-existing `qwen3.6` variants that a colleague may have an alias pointing at, and
deleting them would free nothing anyway. The bare-tag footgun they represent is documented in
`results/inventory-67.txt` rather than fixed by deletion.

### 11b. Final state

| | |
|---|---|
| unique weight blobs on disk | **145.24 GiB** |
| what summing tag sizes reports | 389.91 GiB |
| tags | 18 (from 32) |
| freed by this project's cleanup | **69.85 GiB** |
| of which pre-existing tags removed | `qwen3.6:27b-mtp-q8_0` ×3 and `qwen3.5:9b` ×2, both on explicit instruction |

Six tags are ours and stay: the `nemotron-3.5-lightning` family (kept on request),
`north-mini-code-1.0:q4_K_M-ctx256k-agentic`, `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic`, and
`qwen3.6:27b-q4_K_M-ctx128k-agentic` — the dense proxy Stage A will be compared against.

---

# Stage A — Qwen3.8, measured

Everything from §12 on was measured on **2026-08-27**, on **Ollama 0.32.15**. Everything
before it was measured on **0.32.9**. §13 establishes what that difference is worth, and it
is not nothing — read it before comparing a Stage A number to a Stage B one.

## 12. The blocker cleared, and what the registry actually ships

`plan.md` §1 parked this stage behind one thing: `.67` ran Ollama 0.32.9 and every Qwen3.8
manifest carries `"requires":"0.32.12"`, so the registry answered HTTP 412 before a byte
moved. On 2026-08-27 both boxes report **0.32.15** — the target `market_research.md` §1
recommended over the 0.33.0 pre-release.

```console
$ curl -s http://192.168.100.67:11434/api/version
{"version":"0.32.15"}
$ curl -s http://192.168.100.37:11434/api/version
{"version":"0.32.15"}
```

Manifests resolved before pulling, so the layer geometry is known rather than inferred:

| tag | weights blob | total | params digest |
|---|---|---|---|
| `qwen3.8:27b-q4_K_M` | `f5f1dd8920d4` 15.656 GiB | 16.52 GiB | `448d2943…` |
| `qwen3.8:27b-mtp-q4_K_M` | `f5f1dd8920d4` **same blob** | 16.52 GiB | `906ee87b…` |
| `qwen3.8:27b` *(default tag)* | `f5f1dd8920d4` **same blob** | 16.52 GiB | `906ee87b…` **identical to mtp** |
| `qwen3.8:27b-q8_0` | `2bb227142898` 27.052 GiB | 27.92 GiB | `448d2943…` |

Three findings, none of which needed a benchmark:

**12a. MTP is a params layer, not a model.** A1 and A2 are the same 15.656 GiB blob. Measured
cost of the second tag: **1 second**.

```console
$ time curl -sN .../api/pull -d '{"model":"qwen3.8:27b-mtp-q4_K_M"}'
"status":"pulling 906ee87bde6c" … "status":"success"
A2 pull took 1 s
```

**12b. `qwen3.8:27b` — the tag a person types — is the MTP build.** Its params digest is
byte-identical to `27b-mtp-q4_K_M`'s. Pulling the obvious name silently enables speculative
decoding. §15 measures what that costs, and it is not free.

**12c. The shipped params are clean of v2's expensive footgun, and still need baking.**

```
27b-q4_K_M      min_p 0  presence_penalty 0  repeat_penalty 1  temperature 1  top_k 20  top_p 0.95
27b-mtp-q4_K_M  draft_num_predict 4  + the same six
```

`presence_penalty` is 0 — v2's 31–35% throughput tax is fixed upstream. **Neither ships
`num_ctx`**, so both inherit the 16,384 default. §17 confirms the cliff that creates is
still live on 0.32.15.

A1 pulled in **10m18s** for 16.81 GB — **≈27 MB/s**, not the 12 MB/s v1's log gave. The
`plan.md` §4 budget of ~25 min per q4 tag was 2.4× pessimistic.

### 12d. What `/api/show` says

```
capabilities: ['completion', 'vision', 'tools', 'thinking']
family qwen35 · parameter_size 27.3B · quantization Q4_K_M
qwen35.block_count                  65
qwen35.context_length               262144
qwen35.attention.head_count         24
qwen35.attention.head_count_kv      4
qwen35.attention.key_length         256
qwen35.attention.value_length       256
qwen35.full_attention_interval      4      <-- the important one
qwen35.rope.freq_base               10000000
```

**`full_attention_interval 4` means Qwen3.8 is not a naive dense model.** Only every fourth
layer runs full attention; the rest are sliding-window. §14 measures whether Ollama honours
that, because it decides whether a "dense 27B" can hold a Claude Code window at all.

## 13. The version delta — 0.32.15 re-ranks the entire field

**This is the largest finding of Stage A, and it is not about Qwen3.8.**

`plan.md` §2 C1 required the control be re-measured on the new runtime before any Qwen3.8
number was taken, because otherwise every comparison in this repo confounds *model* with
*runtime version*. `stage_a_plan.md` §5 set the decision rule in advance: within ±5% the v3
tables stand; outside it, every cross-version comparison gets annotated and the delta is
reported as a finding in its own right.

Two models were re-measured rather than one, on the reasoning that one model moving could be
that model and two models moving is the runtime. It turned out to need all four.

Generation tok/s at the 2,000-word prompt, same harness, same seed, same box:

| model | 0.32.9 | 0.32.15 | delta |
|---|---|---|---|
| `qwen3.6:35b-a3b-q4_K_M-agentic` *(control)* | 130.04 | **130.04** | **0.0%** |
| `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic` | 70.02 | **104.14** | **+48.7%** |
| `north-mini-code-1.0:q4_K_M-ctx256k-agentic` | 83.55 | **133.73** / 131.98 | **+60.1%** |
| `nemotron-3.5-lightning:30b-ctx256k-agentic` | 43.9 † | **140.75** / 135.47 | **+221%** |

† nemotron's baseline is v2's number, quoted in §10, not a v3 re-run.

The two outliers were each run twice because a +221% single measurement is not a result.
Both reproduce: nemotron 140.75 then 135.47; north-mini 133.73 then 131.98.

**The control is the point.** It did not move — 130.04 both times, to two decimals, with
prefill up 1.7%. So this is not a box that got faster, a thermal difference, or a harness
change. **0.32.15 contains an optimisation that the qwen3.6 MoE path does not benefit from
and the Cohere, Gemma and Mamba-2 paths benefit from enormously.**

### 13a. Consequences, stated plainly

**The v3 verdict was measured on a runtime that no longer exists on this box, and the
ranking it produced is no longer the ranking.** Generation @2k, then and now:

| | on 0.32.9 | on 0.32.15 |
|---|---|---|
| 1 | **incumbent 130.0** | **nemotron 138.1** *(mean of 2)* |
| 2 | laguna 119.5 | **north-mini 132.9** *(mean of 2)* |
| 3 | north-mini 83.6 | **incumbent 130.0** |
| 4 | gemma4 70.0 | gemma4 104.1 |

The incumbent went from *first by 9%* to *third*, without changing. Prefill @35k moved much
less — gemma4 5,740 → 5,774 (+0.6%), the incumbent 3,911 → 3,996 (+2.2%), north-mini
4,331 → 4,384 (+1.2%), nemotron 3,050 → 2,797 (−8.3%) — so the optimisation is in the decode
path, not the prefill path.

**Not re-measured, and therefore not comparable:** `laguna-xs-2.1`, `muse-glimmer` and
`qwen3.6:27b-q8_0` were deleted in §11 and their numbers are 0.32.9 only. Laguna's 119.5 in
particular cannot be ranked against the table above — it is not a fair third place, it is an
unmeasured one. Every laguna and muse-glimmer figure in this repository should be read as
"on 0.32.9", and the T1–T7 gate results, being pass/fail, are the only part of their record
that survives the version change unqualified.

## 14. The window — 131,072, and hybrid attention is why

`kv-probe.sh`, `--port 11434` as always:

| num_ctx | total | in VRAM | % GPU |
|---|---|---|---|
| 32,768 | 19.602 GB | 19.602 | **100%** |
| 65,536 | 21.410 GB | 21.410 | **100%** |
| 131,072 | 26.242 GB | 26.242 | **100%** |
| 262,144 | 35.280 GB | 33.982 | **96%** — spills |

**Usable window: `num_ctx 131072`.** 262,144 allocates but pushes 1.3 GB into system RAM, and
`README.md` finding #2 puts the cost of a 12.5% spill at 5.3×. A 4% spill is not worth
finding the exact price of.

`stage_a_plan.md` §3 predicted, before the measurement: *"A1 reaches 131,072 at 100% GPU and
does not reach 262,144."* That is what happened.

### 14a. Ignore the probe's own SWA verdict here

`kv-probe.sh` prints `-> NAIVE (full KV for all 52 layers)`. **That line is wrong for this
model** and must not be quoted. Its two reference constants (13,312 and 53,248 B/tok) are
hardcoded for muse-glimmer's 52-layer geometry. Qwen3.8 has 65 layers with
`head_count_kv 4` and `key_length 256`, so the correct predictions are:

| | B/token | at 131,072 |
|---|---|---|
| naive — all 65 layers full | 266,240 | 34.9 GB |
| SWA-aware — 65/4 = 16.25 full layers | 66,560 | 8.7 GB |
| **measured** — see §19b | **73,730** | **9.7 GB** |

**Measured is 3.61× cheaper than naive. Ollama honours `full_attention_interval`.** That is
the entire reason a dense 27B holds 131k on this box: naive KV would have cost 34.9 GB for
the cache alone, on top of 17.1 GB of weights.

The 73,730 figure supersedes the 69,131 that `kv-probe.sh`'s least-squares fit prints, and
§19b explains why the fit is the wrong estimator here — briefly, it averages over rungs that
spill and over a low rung that has not amortised a fixed overhead. The marginal cost between
two adjacent rungs that both sit at 100% GPU is the honest number, and it reproduces to the
byte across both quantizations.

The fitted intercept, 17.14 GB, is the weights — consistent with 16.52 GiB of layers.

## 15. Throughput — the pre-registered "no" threshold fires

Both variants baked at `num_ctx 131072`, `presence_penalty 0`, differing **only** in
`draft_num_predict` (0 vs the shipped 4), so MTP is the single variable.

| model | words | prompt_tok | prefill tok/s | **gen tok/s** |
|---|---|---|---|---|
| **A1** `qwen3.8:27b-q4_K_M-ctx128k-agentic` | 0 | 25 | 83.3 | 30.56 |
| | 2,000 | 3,180 | 1,198.0 | **30.39** |
| | 20,000 | 35,102 | 1,427.8 | 27.41 |
| **A2** `qwen3.8:27b-mtp-q4_K_M-ctx128k-agentic` | 0 | 25 | 71.4 | 36.85 |
| | 2,000 | 3,180 | 765.8 | **36.58** |
| | 20,000 | 35,102 | 767.0 | 35.01 |

### 15a. A1 against the field

`stage_a_plan.md` §6 pre-registered the threshold: *"A1 lands under ~40 tok/s → Qwen3.8's
benchmark wins do not transfer into an agentic loop on this box."*

**A1 generates at 30.4 tok/s.** The threshold fired.

| | A1 Qwen3.8 27B | incumbent | ratio |
|---|---|---|---|
| generation @2k | **30.4** | 130.0 | **4.3× slower** |
| prefill @35k | **1,428** | 3,996 | **2.8× slower** |
| vs. nemotron on 0.32.15 | | 138.1 | 4.5× slower |

And against the dense proxy §9 stood in for it with — `qwen3.6:27b-q4_K_M` at **31.04**
tok/s on 0.32.9. **Qwen3.8's dense 27B generates at 30.4 where Qwen3.6's dense 27B generated
at 31.0.** A generation newer, the same shape, the same speed. The proxy was a good proxy,
and shape predicted the outcome exactly as §5 of the README claimed it would.

### 15b. MTP reverses v2's finding — and is still the wrong choice

v2 measured MTP as a straight generation loss (129.2 → 100.6 tok/s). On Qwen3.8 it is the
opposite: **+20.4% generation** (30.39 → 36.58). That is a real gain, and it is the first
time speculative decoding has paid off anywhere in this project.

**It costs 46% of prefill to get it** (1,428 → 767 tok/s at 35k), and prefill is flat across
prompt size — 765.8 at 3k and 767.0 at 35k — where A1's rises with the prompt (1,198 →
1,428). The draft model is being run over the prompt too.

`README.md` finding #2 decides this: an agentic loop re-reads its whole context every turn,
so prefill is what Claude Code pays per tool result while generation covers a few dozen
emitted tokens. Trading 46% of the thing you pay every turn for 20% of the thing you pay
rarely is a net loss for this workload. The 20,000-word row shows it end to end: **A1 total
28.9 s, A2 total 50.9 s — MTP is 76% slower on the realistic prompt.**

**So: use `qwen3.8:27b-q4_K_M`, not `qwen3.8:27b`.** The default tag is the MTP build (§12b),
and for Claude Code the default tag is the wrong one.

## 16. Tool gates and retrieval — capable, within a smaller window

### 16a. T1–T7

```
T1_single_tool        PASS  correct_args
T2_tool_selection     PASS  chose_search_code
T3_multiturn          PASS  used_tool_result
T4_parallel_calls     PASS  2_parallel_calls
T5_complex_schema     PASS  nested_schema_exact_1_edits
T6_needle_4k          PASS  found_at_4411_prompt_tokens
T6_needle_16k         PASS  found_at_17861_prompt_tokens
T6_needle_60k         PASS  found_at_72419_prompt_tokens
T6_needle_120k        FAIL  missed_at_65538_prompt_tokens
T7_tool_at_long_ctx   PASS  3/3_at_53283_tokens[PASS,PASS,PASS]
```

**9/10 — and the one FAIL is the window, not the model.** T4 and T7, the two gates laguna
failed, both pass: parallel calls are emitted in parallel, and three of three tool calls
land at 53,283 tokens. On the property `README.md` ranks first, Qwen3.8 is sound.

### 16b. The 120k FAIL is a truncation artifact, and here is the proof

`needle-v2.sh` at `--num-predict 2048`, five depths:

| depth | prompt_eval | verdict | answer |
|---|---|---|---|
| 40,000 words | 72,419 | **PASS** | `CRIMSON-PANGOLIN-4471` |
| 55,000 words | 100,361 | **PASS** | `CRIMSON-PANGOLIN-4471` |
| 65,010 words | **119,015** | **PASS** | `CRIMSON-PANGOLIN-4471` |
| 72,006 words | **65,538** | FAIL | *"The provided text does not contain a deployment passphrase."* |
| 80,003 words | **65,538** | FAIL | *"There is no deployment passphrase mentioned…"* |

The two failing rows report **the identical prompt_eval_count, 65,538**, for documents 8,000
words apart. That is not a model behaviour — it is `131072 / 2 + 2`, the half-window
truncation documented in `README.md` finding #6. The needle is buried mid-document, the
truncation discards it, and the model then answers correctly about the text it was actually
given. It is not failing to retrieve; it is being handed a different document.

**Deepest verified retrieval: 119,015 tokens — 90.8% of the baked window.** That ratio is the
best in the field: north-mini retrieves 201,737 of the 500,000 it allocates (40%), and the
incumbent 146,957 of 262,144 (56%). Qwen3.8's window is the smallest here and the most
completely usable.

### 16c. Vision — PASS

Same fixture as v2 (`../ollamaClaudeCode_v0/failingOutput.png`), same prompt. 71.2 s,
2,633 characters. It read the version string, the model tag and the working directory out of
the screenshot correctly, and described the CMake task in the prompt box. Not a
capability-flag check — an actual correct reading.

## 17. The bare-tag cliff still exists on 0.32.15

`cliff-probe.sh`, bare tag vs baked tag, on the new runtime:

| prompt | `qwen3.8:27b-q4_K_M` *(bare)* | `…-ctx128k-agentic` *(baked)* |
|---|---|---|
| ~4k | 4,090 tok · **tool_use** | 4,090 tok · **tool_use** |
| ~16k | 16,090 tok · **tool_use** | 16,090 tok · **tool_use** |
| ~32k | **16,386 tok · end_turn · NO tool call** | 33,290 tok · **tool_use** |
| ~50k | **16,386 tok · end_turn · NO tool call** | 53,090 tok · **tool_use** |

Unchanged from 0.32.9. The bare tag pins at 16,386 tokens and **stops calling tools
entirely** — no error, no warning, `stop_reason` just becomes `end_turn`. The upgrade fixed
nothing here, and `README.md` finding #6 stands on the new runtime: every model on this box
is unusable with Claude Code until a window is baked.

## 18. End to end — it drives Claude Code, slowly

Same fixture, same scoring as §7: `pytest` green afterwards, `stats.py` changed, `tests/`
untouched.

| model | verdict | wall | turns | tools |
|---|---|---|---|---|
| `qwen3.8:27b-q4_K_M-ctx128k-agentic` | **PASS** | **111 s** | 19 | `Bashx4,Readx3,Editx1` |
| `qwen3.6:35b-a3b-q4_K_M-agentic` *(incumbent)* | PASS | 46 s | 16 | `Bashx4,Readx3,Editx1` |

It fixed the bug properly — read the failing test, edited only the source, re-ran the suite,
did not touch the assertion. The tool histogram is **identical** to the incumbent's:
`Bashx4,Readx3,Editx1`. No blind `Write`, no thrash.

**And it took 2.4× as long for the same work.** 111 s lands it squarely in the dense band
this project has measured all along (113–179 s) and outside the MoE band (42–60 s), which is
now nine models deep with no exceptions. §7's finding — capability is flat, wall clock is
not, and the split falls on architecture — survives Qwen3.8 intact.

## 19. The q8_0 rung — and the box's real VRAM ceiling, measured twice

`plan.md` §2 gated A3 on "runs only if A1 earns it", and at 30.4 tok/s A1 did not. It was
pulled and measured anyway, on explicit instruction, to answer the fit question for the
quality rung with a measurement instead of a prediction. **Both rungs measured here are
q4_K_M or q8_0 — no sub-4-bit quantization was pulled, benchmarked or considered.**

### 19a. The ladder

| num_ctx | total | in VRAM | % GPU |
|---|---|---|---|
| 16,384 | 29.199 GB | 29.199 | **100%** |
| 32,768 | 30.407 GB | 30.407 | **100%** |
| 65,536 | 32.823 GB | 32.823 | **100%** |
| 98,304 | 36.084 GB | 34.163 | 95% — spills |
| 131,072 | 38.332 GB | 35.557 | 93% — spills |

**Usable window: `num_ctx 65536`** — half of what q4 holds.

### 19b. 73,730 bytes per token, three times, and the correct estimator

Taking marginal cost only between adjacent rungs that *both* sit at 100% GPU:

| rungs | quant | B/token |
|---|---|---|
| 32,768 → 65,536 | q4_K_M | 55,176 |
| **65,536 → 131,072** | **q4_K_M** | **73,730** |
| **16,384 → 32,768** | **q8_0** | **73,730** |
| **32,768 → 65,536** | **q8_0** | **73,730** |

**73,730 B/token, reproduced to the byte three times across two different quantizations.**
That is exactly what it should be — the KV cache is stored at f16 regardless of how the
*weights* are quantized — and it is the check that the number is real rather than fitted.

It is also exactly `18 × 4096`: 73,728 bytes, where 4,096 B/tok/layer is
`2 (K,V) × 4 kv-heads × 256 head-dim × 2 bytes`. So **18 of the 65 layers hold full KV.**
`full_attention_interval 4` predicts 16–17; the exposed metadata does not say how the
remaining layer or two is accounted for, and no API exposes it, so the 18 is recorded as
measured and not explained.

The model `total = weights + 73,730 × num_ctx` recovers both manifests:

| | implied weights | manifest |
|---|---|---|
| q4_K_M | 16.58 GB | 16.52 GiB |
| q8_0 | 27.99 GB | 27.92 GiB |

Within 0.4%. **This is why `kv-probe.sh`'s least-squares line should not be quoted for either
rung** — it returned 69,131 for q4 (dragged down by the un-amortised 32,768 rung) and 81,354
for q8 (dragged up by two rungs that had already spilled). Same caveat as north-mini's in
`README.md`: a slope fitted across an allocation regime change is meaningless.

### 19c. The 35.5 GB ceiling is now measured twice, a generation apart

v2 established the box's usable VRAM from a single observation
(`../ollamaClaudeCode_v2/muse_ollama.md` §11.4): `qwen3.6:27b-q8_0` at `num_ctx 131072`
asked for **38.33 GB** and only **35.56 GB** stayed resident.

`qwen3.8:27b-q8_0` at `num_ctx 131072` asks for **38.332 GB** and **35.557 GB** stays
resident.

The same two numbers, from a different model generation, eight months of Ollama releases
apart. **`.67`'s usable VRAM is 35.56 GB.** The `40.4 GB` figure that has been carried in
this project's notes as "human-supplied, no VRAM API exists" now has a measured companion
that has reproduced independently, and every memory budget in this repo should use 35.56.

### 19d. Throughput — the quality rung costs a third of the speed

| model | words | prefill tok/s | **gen tok/s** |
|---|---|---|---|
| `qwen3.8:27b-q8_0-ctx64k-agentic` | 0 | 84.2 | 19.49 |
| | 2,000 | 1,246.0 | **19.41** |
| | 20,000 | 1,486.9 | 18.17 |

**19.41 tok/s — 36% slower than q4's 30.39.** And prefill goes *up* 4% (1,487 vs 1,428 at
35k), which is the expected shape: generation is memory-bandwidth-bound and q8 streams
1.7× the bytes per token, while prefill is compute-bound and barely notices.

For the third time, Qwen3.8 lands on its predecessor's number: v2 measured
`qwen3.6:27b-q8_0` at **19.5 tok/s**; Qwen3.8's q8 is **19.41**.

### 19e. Gates and end to end

```
T1 PASS  T2 PASS  T3 PASS  T4 PASS  T5 PARTIAL(schema_ok_strategy=None)
T6_4k  PASS  T6_16k PASS
T6_60k FAIL  missed_at_32770_prompt_tokens
T6_120k FAIL missed_at_32770_prompt_tokens
T7 PASS 3/3_at_53283_tokens
```

**8/10, and both needle FAILs are the same truncation artifact as §16b** — this time at
`32,770 = 65536/2 + 2`, for two documents 40,000 words apart. §16b's proof now holds at two
different window sizes, which is stronger evidence than one.

`cc-session`: **PASS in 137 s**, 17 turns, `Bashx4,Readx2,Editx1`.

### 19f. The T5 PARTIAL is not a quantization effect

Worth chasing, because "the higher-precision rung is the worse tool caller" would be a
genuinely surprising claim. It does not survive being measured.

T5 re-run 10 times per rung, plus the harness's own run — n=11 each:

| | clean | failures |
|---|---|---|
| q4_K_M | **11 / 11** | — |
| q8_0 | **9 / 11** | one `no_tool_call`, one runaway emitting **156 edits** for a 2-file change |

2/11 versus 0/11 is not a significant difference (Fisher's exact, p ≈ 0.48). **The PARTIAL is
not established as a quantization effect and must not be reported as one.**

What it *does* establish is a methodological caveat that applies to every single-shot gate
result in this repository: **the battery runs at the model's shipped sampling parameters —
`temperature 1`, `top_p 0.95`, `top_k 20` — not at temperature 0.** T1–T5 are one sample
each, so any of them can flip on a re-run. T7 already samples 3× and is the more trustworthy
gate for that reason. Runs 4–10 were identical for both rungs (`strategy='squash'`,
`edits=2`), so the instability is concentrated and occasional rather than uniform.

## 20. MTP end to end — the prefill penalty needs a big prompt to show up

§15b concluded MTP is a net loss for agentic work, from the 20,000-word tokrate row: A1
28.9 s vs A2 50.9 s, a 76% penalty. The end-to-end session does **not** reproduce that:

| model | verdict | wall | turns | tools |
|---|---|---|---|---|
| `qwen3.8:27b-q4_K_M-ctx128k-agentic` | PASS | **111 s** | 19 | `Bashx4,Readx3,Editx1` |
| `qwen3.8:27b-mtp-q4_K_M-ctx128k-agentic` | PASS | **109 s** | 17 | `Bashx4,Readx3,Editx1` |

**109 s vs 111 s — indistinguishable.** Stated plainly because it qualifies §15b rather than
confirming it: the `cc-session` fixture is a two-file repository, so its prompts are short,
and at short prompts MTP's +20% generation roughly cancels its −46% prefill.

So the honest form of the §15b recommendation: **MTP is a net loss on large contexts and a
wash on small ones.** Claude Code on a real repository lives at the large-context end — that
is the whole premise of `README.md` finding #2 — so `qwen3.8:27b-q4_K_M` remains the right
tag over `qwen3.8:27b`. But the evidence for that is the 35k-token tokrate row, not this
session, and the session is recorded here as the place where the effect did not appear.

## 21. Stage A summary — the three rungs

| | **A1 q4_K_M** | **A2 mtp-q4_K_M** | **A3 q8_0** |
|---|---|---|---|
| weights | 16.52 GiB | 16.52 GiB *(same blob)* | 27.92 GiB |
| **max window @100% GPU** | **131,072** | 131,072 | **65,536** |
| resident there | 26.24 GB | 26.24 GB | 32.82 GB |
| **generation @2k** | **30.39 tok/s** | 36.58 | 19.41 |
| **prefill @35k** | **1,428 tok/s** | 767 | 1,487 |
| 20k-word turn, total | **28.9 s** | 50.9 s | 32.0 s |
| tool gates | **9/10** | not run | 8/10 |
| T5 over n=11 | **11/11** | not run | 9/11 |
| deepest verified retrieval | **119,015** | not run | ≤32,768 *(window-bound)* |
| Claude Code session | PASS 111 s | PASS 109 s | PASS 137 s |
| vision | PASS | not run | not run |

**The rung to use, if you use Qwen3.8 at all, is `qwen3.8:27b-q4_K_M` baked at
`num_ctx 131072`.** A2 is the same weights with a worse prefill profile and is what you get
by typing the obvious tag name. A3 costs 36% of the generation speed and half the window to
buy precision this workload has not been shown to need — every capability gate it passes,
A1 also passes, and A1 passes one more.
