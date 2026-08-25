# v3 benchmark plan — Qwen3.8 and the 2026-08 field

Written **2026-08-25**, before any measurement. The evidence behind the model choices is in
[`market_research.md`](market_research.md). Nothing here is a result.

The question v3 answers is the same one v2 answered, against a new field:
**which local model should drive Claude Code on `192.168.100.67`?** — where "drive" means
tool calling works, the context window is real, and the thing is fast enough to iterate
with. The incumbent to beat is `qwen3.6:35b-a3b-q4_K_M-agentic` @ 262144 at **131.4 tok/s**.

---

## 1. What we need from you before stage A can run

**`.67` is on Ollama 0.32.9. Every Qwen3.8 tag requires 0.32.12.** The registry refuses the
pull with HTTP 412 (`market_research.md` §1). We have no SSH to `.67` and the box belongs to
a colleague, so the upgrade is not ours to do.

> **Decision 1 — the upgrade. SETTLED 2026-08-25: requested from the owner of `.67`, not
> possible right now.** The target is **0.32.15** (current stable; clears the gate, carries
> the two Qwen3.8 message-handling fixes) rather than the 0.33.0 pre-release. Consequence:
> **Stage A is parked and Stage B runs first.** When the upgrade lands, Stage A runs *and*
> the control is re-measured on the new runtime — see §6.

> **Decision 2 — disk. SETTLED 2026-08-25: pull everything, delete nothing.** Every tag this
> project pulls stays on `.67`. Peak footprint is ≈92 GB of q4 weights plus 30 GB if the q8
> rung runs. Free space is not exposed by any API and we have no shell, so the first symptom
> of a full disk would be a failed write — which is why pulls are sequential, and why Stage B
> going first limits the blast radius to models we can bench today.

**Stage B does not depend on either decision** — `laguna-xs-2.1`, `north-mini-code-1.0` and
`gemma4:26b-a4b` all clear 0.32.9 today. If the upgrade is slow to arrive, B runs first and
A lands later, at the cost of re-running the control in the same session as A.

## 2. The models to bench

Seven, in three groups. Every one is 3B–4B-active MoE or is there for a reason that
survives being slow.

### Stage A — the point of the exercise *(blocked on Decision 1)*

| # | tag | GB | why it is in |
|---|---|---|---|
| A1 | `qwen3.8:27b-q4_K_M` | 17.74 | the model you asked about. Dense 27B, 256K, vision, Apache-2.0 |
| A2 | `qwen3.8:27b-mtp-q4_K_M` | 17.74 | same weights + MTP head. v2 measured MTP as a **net loss** here (129.2 → 100.6 tok/s at the shipped `draft_num_predict 4`); this re-tests that on a new generation, and it is cheap because the sweep already exists |
| A3 | `qwen3.8:27b-q8_0` | 29.98 | the quality rung. Expected to be *window*-limited, not weight-limited: v2's dense q8 topped out at `num_ctx 81920`. Runs only if A1 earns it |

### Stage B — the new MoEs that run today

| # | tag | GB | why it is in |
|---|---|---|---|
| B1 | `laguna-xs-2.1:q4_K_M` | 20.27 | 33B **3B-active**, 256K — the only new model shaped like the incumbent, so the only one that can plausibly beat it on tok/s |
| B2 | `north-mini-code-1.0:q4_K_M` | 18.59 | Cohere, 30B **3B-active**, trained for agentic SWE across SWE-Agent/OpenCode/Terminus 2, advertises **488K** context |
| B3 | `gemma4:26b-a4b-it-q4_K_M` | 17.99 | 4B-active MoE with vision *and* audio; a different vendor's tool-calling template is worth one gate run |

### Stage C — the control

| # | tag | why it is in |
|---|---|---|
| C1 | `qwen3.6:35b-a3b-q4_K_M-agentic` | **mandatory.** Already on the box, already measured at 131.4 tok/s — but on Ollama 0.32.9. If `.67` moves to 0.32.15, *every v2 number becomes cross-version* and the incumbent must be re-measured in the same session as the challengers or the comparison is worthless |

Excluded candidates and the reason for each are in `market_research.md` §4. The short
version: everything else new is 65 GB–2.8 T, or has no tool calling.

## 3. Protocol

Reuse v2's harness rather than writing a new one — it already encodes six findings that
cost real time to discover. v3 gets **copies** of `idle.sh`, `tokrate.sh`, `head2head.sh`,
`kv-probe.sh`, `cliff-probe.sh` and `needle-v2.sh`, with exactly two documented changes:

1. `idle.sh`'s ownership regex extended to `qwen3.8:|laguna-|north-mini-|gemma4:`, so the
   new tags are ours to unload and everything else is still waited out, never evicted.
2. the candidate list.

Copies rather than edits in place: v2's README is a published verdict, and mutating the
harness that produced it would break its provenance.

**Footgun, hit on the first run:** `kv-probe.sh` defaults to `127.0.0.1:11435`, not to
`.67:11434`. Passing `--host` without `--port` sends every create, load and `/api/ps` to a
port with nothing behind it, and the failure surfaces as a JSON decode error rather than a
connection error — which reads like a broken model. **Always pass `--port 11434`.** The
default is left alone rather than patched, to keep the v3 harness diff to the one documented
change; the cost is this line of documentation. Confirmed harmless: because the creates went
nowhere, no probe tags were orphaned on `.67`.

Per model, in this order, with `./idle.sh` asserted between **every** stage:

| step | what | why it is not optional |
|---|---|---|
| 1 | **bake an `-agentic` variant** via `/api/create`: `num_ctx` set, `draft_num_predict 0`, `presence_penalty 0` | a bare tag inherits a **16,384** window on `/v1/messages` and **tool calling silently stops** past it |
| 2 | **residency** — `/api/ps` must read 100% GPU | a 12.5% spill measured **5.3× slower**, which is larger than the real gap between any two models here |
| 3 | **`kv-probe`** ladder → the largest `num_ctx` that stays 100% GPU | the window a model advertises is not the window this box can hold |
| 4 | **`tokrate`** at 0 / 2k / 20k words → generation tok/s + prefill tok/s | the headline number, and prefill is what an agentic loop actually pays |
| 5 | **tool gates T1–T5** against `/v1/messages` | Ollama's `tools` capability label is a manifest field, not a test |
| 6 | **`needle-v2`** at depth, same document for every model | retrieval at the *baked* window, not the advertised one. `num_predict` ≥ 128 — v1's 64 manufactured failures |
| 7 | **`cliff-probe`** bare tag vs baked tag | confirms the half-window truncation cliff still exists on whatever version `.67` ends up running |
| 8 | **vision** (A1/A3/B3 only), one screenshot, same one v2 used | comparable to v2's numbers |

**Stage 9 — does it actually drive Claude Code?** The bench above measures a server. What
you asked for is whether Claude Code works *with all the skills and capabilities*, which is
a different claim. For the top two finishers only: a real session per model, driven by
`claude --model …`, over a fixed script — read a file, edit it, run a build, use a Task
subagent, invoke a skill, do a multi-tool turn — scored on completion and wall-clock, not
on tok/s. Slow and manual, which is why it runs on two models rather than seven.

## 4. Budget and etiquette

- **Pull time ≈ 12 MB/s**, measured from v1's pull log (17.08 GB in 23m24s). So ~25 min per
  q4 tag, ~42 min for the q8. Stage A+B q4 pulls ≈ **2.1 h wall clock**, sequential — never
  parallel, because parallel pulls split the link and make a disk-full failure impossible to
  attribute.
- **Bench time** ≈ 30–45 min per model for steps 1–8. Seven models ≈ 4–5 h, plus stage 9.
- **`.67` is shared.** `idle.sh` unloads only tags this project owns and *waits out*
  anything foreign rather than evicting it. On 2026-08-13 a colleague's session held
  32.54 GB with a 2 h `keep_alive`; an unguarded unload would have cost them a 70 s reload
  mid-session. That guard stays.
- Nothing gets deleted on `.67` without Decision 2.

## 5. Deliverables in this directory

| file | what it will be |
|---|---|
| `market_research.md` | the survey — **written** |
| `plan.md` | this file — **written** |
| `README.md` | the verdict, one page, in v2's format |
| `qwen38_eval.md` | the full argument: every measurement, methodology, what we got wrong |
| `results/*.tsv` | machine-readable throughput / KV / needle rows |
| `results/inventory-67.txt` | the tag inventory after the run |
| `*.sh` | the harness copies described in §3 |
| `shell_aliases.md` | updated `claude-ol*` functions **only if** the recommendation changes |

Commits are atomic and Conventional, one logical change each, with a body that says what was
measured and what was **not**. A model's data lands with the document paragraph that
interprets it, not separately.

## 6. What could invalidate this plan

- **The upgrade does not happen.** Then Stage A is dead, v3 becomes a three-model report on
  Laguna / North-mini / Gemma4, and it should say so in the title rather than quietly
  shipping a Qwen3.8 report without Qwen3.8 in it. As of 2026-08-25 this is the live risk,
  not a hypothetical: the upgrade is requested but cannot happen yet.
- **There is no MoE Qwen3.8 to fall back on.** Checked rather than assumed — Qwen publishes
  the dense 27B and the 2.4T-A95B Max, nothing between. `Qwen3.8-35B-A3B` is an unreleased
  leak. So "wait for the fast one" is not a strategy available to this project.
- **The upgrade happens mid-run.** Worse than either end state: half the numbers would be
  0.32.9 and half 0.32.15. If it lands mid-run, everything measured before it is discarded
  and re-run.
- **Dense 27B is simply too slow.** Plausible — v2 measured the dense 27B q8 at 18.1 tok/s
  against the incumbent's 131.4. If A1 lands under ~40 tok/s, Qwen3.8's benchmark wins do not
  transfer into an agentic loop on this hardware, and the honest answer is "smarter, and you
  will not want to use it". That is a real possible outcome of this project, and it is worth
  three days of measurement to establish rather than assume.
- **Disk fills on `.67`.** Sequential pulls with a `df`-less server means the first symptom
  is a failed write. Stage B before Stage A limits the blast radius to models we can bench
  today.
