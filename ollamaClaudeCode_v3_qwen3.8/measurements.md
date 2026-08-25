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

**Not deleted, deliberately:** the bare tags of models being kept. Removing them would free
zero bytes (shared blobs) and `.67` is shared — a colleague may have an alias pointing at one.
The footgun they represent is documented in `results/inventory-67.txt` instead.
