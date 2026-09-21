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
| G5 | vision was yes/no plus one qualitative screenshot read | scored it once, at the full baked window — and **retired the category**: all four vision-capable models scored 25/25, so it ranked nothing. The one thing worth keeping is that Tiel reads images at 262,144 with 1.43 GB of headroom, where `qwen3-vl` hit HTTP 500 and had to drop to a 49k tag |
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
4. ~~**Tiel takes the vision slot only if** it scores ≥ gemma4 on the 25 checks.~~
   **Retired 2026-09-17**: every vision-capable model on the box scored 25/25, so the check
   ranked nothing. Vision is reported as a yes/no capability alongside speed, not as a category.
5. **`presence_penalty`.** If T2 is ≥10% faster than T1 on generation with no gate loss, the
   recommended tag is T2 and the shipped tag is documented as a trap.

## 4b. Stage C — CyberTiel, the abliterated sibling (added 2026-09-17)

The user asked to also benchmark `peculiar-ragdoll/Cyber-Tiel-Coder-35B-A3B-GGUF`:
**Huihui-Ornith-1.5-35B-A3B-abliterated** (refusals removed) → the same Sharp template and a
cyber-weighted imatrix. Same architecture and family as Tiel, so it drops into the field as a
**same-quant (Q5_K_XL) abliterated-vs-censored comparison**.

**Feasible here, and run identically to Tiel:** provenance (§C1: tag, SHA256, size, params vs
card), the full S1 server battery (§C2: kv-probe, tokrate with `presence_penalty 0` baked,
gates ×3, needle ladder, vision), and end-to-end sessions (§C3).

**The one hard difference — sessions run sandboxed.** CyberTiel is uncensored; the publisher's
own instruction is to isolate it at the OS level. `cc-session.sh` runs Claude Code with
`bypassPermissions` **on the host**, which is unacceptable for an abliterated agent. So
CyberTiel sessions use `cc-session-sandboxed.sh`: the agent runs in a Docker container with no
host mounts (fixture `docker cp`-ed in/out), read-only rootfs + tmpfs `/work`, non-root,
`--cap-drop ALL`, `no-new-privileges`, pids/memory caps, and a Docker `--internal` network
whose **only** route out is a `socat` relay to `.67:11434` (internet and direct-`.67` both
verified blocked). Every run records an egress self-check. Same fixtures and scoring as the
host harness, so the numbers are comparable; the isolation is the only variable.

**Safety scope (§C4):** the abliteration is documented through *benign* over-refusal probes —
does it engage a defensive security-engineering task without hedging — never HarmBench prompts
or any harmful content. The sandbox, not the model, is the safety boundary.

**Out of scope, stated rather than faked:** SWE-bench-Live and Cybench (multi-hour harnesses,
shared box), the `--n-cpu-moe` / KV-type / reasoning-budget sweeps (Ollama exposes none of
them — those are `llama-server` flags), and the IQ3/Q4/Q6/Q8 quant sweep (disk on a shared
box; Q5 is the tier that matches the Tiel already resident). The report says so plainly and
makes no parity claim from a single run.

## 4c. Narrowing, 2026-09-17 — what is no longer re-benchmarked

After S2/S3 the field split cleanly, so the remaining stages stop re-measuring models that
have now been rejected **twice on the same defect**. Their existing numbers stay in the
report and the tables, labelled; they are simply not run again.

| cut | evidence, across two rounds |
|---|---|
| `nemotron-cascade-2:30b` | v3: 7/10 gates, 50% parallel-call and 87.5% nested-schema failure, 84 turns / 256 s. **v4: 8/10 gates (T2 + T5), 0/3 sessions, hidden 0/18, 3/18, 3/18, 419 s median**, 41 Bash calls and nine blind `Write`s in one run. It is the fastest model on the box on both axes and it cannot finish a three-file change |
| `qwen3.8:27b-q4_K_M` | v3: 30.4 tok/s, 4.3× slower than the field, measured and not recommended. **v4: 30.3 tok/s, 787 s median on the hard fixture.** Its capability is fine (18/18 hidden, three times) — it is simply the wrong shape for this box, and that was already settled |

Kept, because each answers a question the round is about: the two **Tiel** tags and
**CyberTiel** (the subject), **`ornith:35b`** (Tiel's own ancestor), **`qwen3.6:35b-a3b`** (the
control since v1), **`north-mini`** (the incumbent default Tiel has to beat), **`gemma4:26b-a4b`**
(the only other model that scored 18/18 three times) and **`nemotron-3.5-lightning`** (the only
524k window).

The remaining runs are therefore **only** the sandboxed sessions for Tiel and CyberTiel, plus
CyberTiel's two missing probes — see `s6-focused.sh`.

## 4d. Stage C4b — the base-vs-abliterated discriminator (added 2026-09-17)

`refusal-probe.py` (§C4) already showed neither Tiel nor CyberTiel refuses plainly benign
defensive work, so it does not separate them. The one test that can is `dualuse-probe.py`
(`BENCHMARK_HARNESS.md` §6a): nine legitimate-but-refusal-prone security tasks — AES from
scratch, a PoC for a *provided* injection, a lab port scanner, a dictionary attack on a
*self-generated* hash, malware-triage deobfuscation, a fuzzer, a local priv-esc audit, a CTF pwn
explanation. Every one is authorized/local/CTF/defensive; nothing targets a real system, and
genuinely harmful requests are deliberately absent. It scores DID_IT / CAUTIONED / HEDGED /
REFUSED from the reply and does **not** execute anything.

Run against both Tiel tags and CyberTiel, one model per load, identical set. Pre-registered
outcome: if both do everything, abliteration buys nothing even in the grey zone (the expected
result for a lightly-guarded coding base); if the base refuses where CyberTiel complies, that
refusal boundary is the finding. Driver: `s8-dualuse.sh`, queued after the extra gates.

## 4e. Outcome, 2026-09-18 — the field is now fixed at four

The round finished with the official Terminal-Bench harness (120 trials, 0 VOID —
`terminalbench/official/OFFICIAL_TB_PLAN.md`). **The contenders did not displace the
incumbent:** `qwen3.6` 53%, `north-mini` 50%, Tiel 37%, gemma4 30%, ornith 30%, CyberTiel 27%.

The decision taken on the back of it: **future rounds measure a new contender against four
models and no others.** The standing field, its roles and the retirement list are written down
once, in `BENCHMARK_HARNESS.md` §9a — that is the authority, not this file.

    1  qwen3.6:35b-a3b-q4_K_M-agentic            the default          (capability + reproducibility)
    2  north-mini-code-1.0:q4_K_M-ctx256k-agentic the speed ceiling   (owes an n=2 pass)
    3  gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic   the footprint floor (and the vision slot)
    4  tiel-coder:35b-q5-ctx256k-agentic          context safety      (the only one that refuses)

Retired from testing: **CyberTiel** (last at 27% over 30 trials — abliteration cost capability
and bought nothing; keep the image for the dual-use probe only), **ornith** (superseded by its
own descendant; its job was to be Tiel's ancestor and that is answered), the **shipped Tiel
tag** (never deployed), **nemotron-3.5-lightning** (kept for a 524k window nothing has needed),
and the two already cut in §4c.

Two things this round proved that outlive it:

1. **A single sample is not a result.** n=1 put Tiel at 40% and CyberTiel at 20%; n=3 put them
   at 37% and 27%. Both were wrong, in opposite directions, and the flips nearly cancelled — so
   the headline barely moved while three of ten tasks were coin-flipping underneath it.
2. **The dangerous failure is the confident one.** On `oom`, seven of nine failures relocated
   the cache to `/tmp`, satisfied the user's literal request, and reported success in accurate,
   well-caveated prose — while the default cache the test reads stayed empty. See
   `terminalbench/official/analyse-task.py`.

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

## 7. Next round — picked up 2026-09-21 or later

Written down 2026-09-18 at the end of the round so none of it has to be reconstructed.
Ordered: **nothing below is worth doing before item 1**, because item 1 decides whether the
current ranking means anything.

### 1. Re-run the field at thinking parity — the blocker

The round's model-vs-model comparison is void: `<|think_off|>` is a Sharp-template token, so
Tiel and CyberTiel ran with reasoning disabled (0 blocks in 30 trials each) while qwen3.6, north-
mini, ornith and gemma4 reasoned normally (287 / 373 / 95 / 83 blocks). See
`terminalbench/official/OFFICIAL_TB_PLAN.md` and `BENCHMARK_HARNESS.md` §8b.

    cd terminalbench/official && ./GO_official_tb.sh       # TB_THINKING defaults to on now

The adapter refuses `thinking=off` on a mixed field, so the trap cannot be re-entered. ~4–6 h
for the standing four at n=2. **Until this lands, every slot rationale that rests on
Terminal-Bench capability is provisional — slot 1 (qwen3.6 as the default) most of all.**

Worth running a `thinking=off` arm for **Tiel and CyberTiel alone** in the same round: that is a
legitimate within-family comparison, and it puts a boundary on v4's "2.3× for free" finding,
which was measured on the ledger fixture and never on hard puzzle tasks.

### 2. Close the subset

- Promote a 10th task to replace the defective `nginx-request-logging`: run
  `./validate-subset.py <task>`, answer every UNSTATED line, confirm the oracle scores 100 %,
  then freeze it in its own commit. Nominee: `conda-env-conflict-resolution`.
- Keep `nginx-request-logging` running but unscored; its other 7 sub-tests are real signal.
- Consider reporting `fibonacci-server` separately — it measures scaffold persistence
  (`node server.js &` survives, Claude Code's `run_in_background` does not), not coding.

### 3. Finish the sampling the round left short

- `gemma4` and `ornith` are still at **n=1**. Nothing should be concluded about either.
- Adopt the r/LocalLLaMA method: **5 seeds per configuration with published confidence
  intervals** (`toTest.md` §E). Better discipline than our n=3/n=1 and cheap to do.

### 4. New candidates (`toTest.md` §E)

In priority order: **Qwen3.6-27B** dense (beat the 35B-A3B on tool calling — gate on tok/s
first, dense 27B is the shape that sank Qwen3.8 here), **ManniX OmniMerge v4/v6** (claimed far
faster at equal fix rate; author's own uncontrolled claim), and the **ByteShape quant** of the
Qwen3.6-35B-A3B we already run. Not adding: Ornith-1.5-Heretic (abliterated and lost to its
base — our CyberTiel result, independently reproduced), Qwen-AgentWorld (10 points below base),
BigBang (unsourced).

### 5. Instrument debt

- `vision-bench.py` v2 works and separates the field (Tiel 42/42, qwen3.6 and gemma4 40/42,
  **north-mini 0/42 — no vision capability at all**). Re-check `/api/show` capabilities for any
  new candidate before claiming it can see.
- Token accounting is still `n/a`: the upstream claude-code agent reports no usage to the
  harness. If it ever matters, parse it from the Ollama side instead.

### 6. The standing rule that came out of all this

Three defects this round shared one shape — a compose project name that must be lowercase, a
task whose test contradicts its instruction, a thinking flag only two models honour. **None of
them announced itself; each looked like a model result.** The countermeasures are now in the
harness (§0, §8a, §8b) and the instruments (`validate-subset.py`, oracle gate, VOID/DEFECT
accounting, transcript verification of every flag). Use them before trusting a surprise — and
when an outside ranking disagrees with ours, treat the disagreement as a bug report about us
first.

---

## 8. The 2026-09-21 round — parity first, then the two candidate classes

Written **2026-09-21**, before anything ran. It replaces the ordering in §7 with the one the
day's brief actually asks for: **compare only what is almost comparable, spend the box on the
winner group and on the genuinely new models, and do not re-run a round for a cosmetic change.**

### 8.0 What was decided before any model was loaded

| decision | reason |
|---|---|
| **The subset is not touched.** `conda-env-conflict-resolution` stays unpromoted; 10 tasks run, 9 scored, `nginx` run-but-unscored | it buys ~11% granularity on a rate and costs a validation cycle, a subset change and comparability with round 1 — while confounding the one variable this round exists to isolate. Recorded in `subset.txt`, discarded, not run |
| **Thinking parity is still item 1** | the entire model-vs-model result of 2026-09-18 is void without it (§7.1, harness §8b). Nothing measured today is ranked against anything until the field is re-run at parity |
| **Candidates are screened before they are benchmarked** | 6 plausible new tags exist; the box holds one model and the round holds four comparators. The screen is cheap and pre-registered below, so it cannot be argued with after the fact |
| **README's verdict was corrected first** | it still named Tiel "the default" on 09-17 evidence while `BENCHMARK_HARNESS.md` §9a named qwen3.6, on evidence since voided. Two answers to "which model is the default" in one repo is a defect in its own right |

### 8.1 What fits — hardware and runtime screen, verified on the wire 2026-09-21

**The constraint is 35.56 GB usable VRAM and one resident model.** Measured residency on this
box gives the working rule — the window costs what the family's KV costs, not what the weights
suggest:

| model | weights | resident @262k | KV + overhead |
|---|---|---|---|
| `north-mini` | 18.6 GB | 21.3 GB | +2.7 |
| `gemma4:26b-a4b` | 18.0 GB | 22.34 GB | +4.3 |
| `tiel-coder` Q5 | 27.5 GB | 34.13 GB | +6.6 |
| `qwen3.6:35b-a3b` q4_K_M | 23.9 GB | 32.68 GB | +8.7 |

**Working ceiling: ~26 GiB of GGUF weights** for a 262k window on the `qwen35moe` family, and
that is already the tightest fit in the project. Sizes below are real file sizes from the HF
tree API, not card claims.

| candidate | class | tag to pull | GGUF | fits @262k? |
|---|---|---|---|---|
| **ByteShape Qwen3.6-35B-A3B** | M | `hf.co/byteshape/Qwen3.6-35B-A3B-GGUF:Q4_K_S-4.22bpw` | **17.02 GiB** | yes, comfortably (~26 GB) |
| **KAT-Coder-V2.5-Dev** | M | `hf.co/bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF:Q5_K_M` | 23.30 GiB | yes (~33 GB) — tight, take Q4_K_M (19.92) if `/api/ps` spills |
| occamy-1.0 | M | `hf.co/mradermacher/occamy-1.0-i1-GGUF:i1-Q4_K_M` | 19.71 GiB | yes |
| Tiel-Coder **MTP** | M | `hf.co/peculiar-ragdoll/Tiel-Coder-35B-A3B-GGUF-MTP:UD-Q5_K_XL` | 25.13 GiB | yes, at Tiel's own 1.4 GB margin |
| **Qwen3.6-27B** (dense) | D | `hf.co/unsloth/Qwen3.6-27B-GGUF:Q5_K_M` | 18.17 GiB | yes |
| **OmniMerge v4** (Qwen3.6-27B) | D | `hf.co/ManniX-ITA/Qwen3.6-27B-Omnimerge-v4-GGUF:Q5_K_M` | 17.91 GiB | yes |
| **OmniMerge v6** (Qwen3.8-27B) | D | `hf.co/mradermacher/Qwen3.8-27B-Omnimerge-v6-GGUF:Q5_K_M` | ~18.2 GiB | yes |
| Nail-Qwen3.6-35B-A3B | M | `…/Nail-Qwen3.6-35B-A3B-GGUF:UD-Q5_K_XL` | 24.77 GiB | yes — but it is the *exam* sibling, not a coder |
| Dirk-Qwen3.8-27B | D | `…/Dirk-Qwen3.8-27B-GGUF:UD-Q5_K_XL` | 19.44 GiB | yes |
| Q8 rungs of any 27B, Q6_K_XL of any 35B | — | — | 26–30 GiB | **no** — weights alone eat the KV budget |

**Two runtime facts settle the rest:**

1. **Do not pull an `-MTP` build except as a deliberate experiment.** Ollama *does* honour the
   MTP head (`draft_num_predict 4`), and v3 measured what it costs on this box: **+20%
   generation for −46% prefill**. On 0.32.15 that was a net loss. 0.33.3 caches prefixes (§2 of
   `measurements.md`), so the prefill penalty is now paid **once per session instead of once per
   turn** — which makes MTP newly interesting rather than settled. It is an experiment with a
   named hypothesis, not a default choice, and it is run last.
2. **Below 4 bits is out of scope**, standing rule. That removes ByteShape's 3.48/3.80/3.93 bpw
   rungs; only the 4.15–4.22 bpw files qualify.

### 8.2 The two comparability classes — and what may be compared with what

The brief is "compare things which are almost comparable". Written down, that means:

- **Class M — 35B-A3B MoE, `qwen35moe`, 4–5 bpw.** `qwen3.6:35b-a3b` (control), `tiel-coder`,
  ByteShape, KAT-Coder, occamy. Same architecture, same active-parameter budget, same box
  behaviour. **Rank these against each other.**
- **Class D — dense ~27B, 4–5 bpw.** Qwen3.6-27B, OmniMerge v4/v6, Dirk. Their class anchor is
  already measured and is not re-run: `qwen3.8:27b` at **30.3 tok/s, 787 s ledger median,
  18/18 hidden ×3** — capable and the wrong shape for this box. **Rank these against each other
  and against that anchor**, never directly against a Class M tok/s number.
- **Class S — small MoE.** `north-mini` (speed ceiling), `gemma4:26b-a4b` (footprint floor).
  They hold axes, not ranks.

Across classes, only **axis** comparisons are made: capability on the same fixture, footprint at
the same window, context behaviour at overflow. A tok/s table spanning all three classes is a
category error and the round does not print one.

### 8.3 The screen — pre-registered, cheapest test first

A candidate reaches the Terminal-Bench round only by passing **all three**, in order. Each is
recorded whether it passes or not; a model cut at G1 still gets its row.

| gate | test | pass condition | why this and not tok/s alone |
|---|---|---|---|
| **G1 fit** | bake `-agentic` (num_ctx 262144, `presence_penalty 0`), load, read `/api/ps` | `size_vram == size` (100% GPU) at ≥131,072 | a 12.5% spill cost 5.3× in v1 |
| **G2 tools** | `agentic-test.sh` battery | ≥9/10, and no *reproducible* failure (≥3 of 8 re-runs) | standing rule 2: gates beat speed. It rejected laguna and cascade-2 |
| **G3 turn economy** | `cc-session.sh --fixture hard --runs 3 --thinking on` | median wall ≤ **2.5× the best standing model** (≤150 s) **and** median hidden ≥16/18 | **tok/s alone mispredicts.** `qwen3.8:27b` scored 18/18 three times and still took 787 s; `nemotron-cascade-2` was the fastest model on the box and finished nothing. What the user waits for is turns × latency (v3 §3) |

Generation tok/s, cold prefill and residency are **measured and reported for every candidate**,
they are simply not the gate.

### 8.4 The round

| stage | what | field | ≈ |
|---|---|---|---|
| **P0** | docs corrected, subset decision recorded, this plan | — | done |
| **P1** | pull → bake → provenance → G1/G2/G3, one model at a time, delete anything cut at G1 | the candidates of §8.1, in the order listed there | ~40 min each |
| **P2** | **the thinking-parity Terminal-Bench re-run** — the blocker from §7.1 | the standing four, `TB_THINKING=on`, n=1 then n=2 | 7–10 h |
| **P3** | the same subset, same settings, for every candidate that survived §8.3 | survivors only, n=2 | ~1.5 h each |
| **P4** | a `thinking=off` arm for **Tiel alone** — the within-family boundary on v4's "2.3× for free", which was measured on the ledger fixture and never on hard puzzle tasks | `tiel-coder`, n=2 | ~1 h |
| **P5** | summarise, regenerate the report, rewrite the verdict from the TSV | — | — |

**P2 before P3.** A candidate measured against a void baseline is a wasted afternoon, and the
standing four at parity *is* the baseline. If the box is taken or the day runs out, P2 alone is
the round; everything after it is optional.

**Budget note, corrected:** §7 estimated 4–6 h for P2. Round 1 took 09:36→15:29 wall for six
models with thinking **off** on two of them (n=1 ≈ 25–40 min/model, n=2 ≈ 40–70 min/model).
With reasoning **on** for all four, 7–10 h is the honest figure, and `TB_PHASE=1` / `TB_PHASE=2`
exists to split it across two windows.

### 8.5 Pre-registered outcomes — fixed now so the results cannot pick them

1. **P2 is the new baseline, whatever it says.** If the parity re-run reverses the 09-18
   ordering, the 09-18 ordering is discarded, not defended. If it confirms it, the "contenders
   did not displace the incumbent" verdict becomes evidence instead of a claim.
2. **A candidate takes a standing slot only by beating that slot's holder on that slot's own
   axis** (harness §9a), measured in the same session, at n ≥ 2.
3. **The dense 27Bs are expected to fail G3.** `qwen3.8:27b` is the class anchor at 787 s. If a
   dense 27B passes anyway, that is the finding of the round and the OmniMerge turn-economy
   claim is the mechanism to look at — not a reason to relax the gate afterwards.
4. **ByteShape is a quant question, not a model question.** Same weights as the control, a
   different quant house, 17.02 GiB against 22.29. If it matches the control within noise it
   reclaims 5 GB of VRAM; if it loses, our quant choice is vindicated and the rung is retired.
   Either way it is compared **only** against `qwen3.6:35b-a3b`.
5. **Nothing is deleted from the box that this round did not pull**, and anything cut at G1 is
   deleted the same session so a shared disk is not held hostage by a rejected candidate.
