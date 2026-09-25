# toTest — models worth a v5 round

Candidates found on the web on **2026-09-17**, not yet benchmarked. Sourced from Hugging Face
and the Ollama library; **every tag here is unverified until Stage 0 of `BENCHMARK_HARNESS.md`
confirms it on the wire** (`/api/show`: real quant, params, capabilities, and the *`template`*
field, not the Modelfile's printed one). Web summaries get sizes and names wrong — treat this as
a shortlist, not a fact sheet.

Hard constraint: **usable VRAM on `.67` is 35.56 GB.** A model whose weights + KV for a usable
window do not sit at 100% GPU is rejected on sight (a 12.5% spill cost 5.3× in v1). That caps
practical candidates at roughly a **Q5 of a 35B**, or a **Q4 of a dense ~30B**.

Already on the box / already judged — do **not** re-list or re-run (see `measurements.md`,
`plan.md` §4c): Tiel, CyberTiel, qwen3.6:35b-a3b, qwen3.8:27b, north-mini, gemma4:26b-a4b,
ornith, nemotron-3.5-lightning, nemotron-cascade-2 *(cut)*, muse-glimmer/laguna *(deleted)*.

---

## A. Same author (peculiar-ragdoll) — the highest-value comparisons

Same "Sharp" template family and quant method as Tiel, so they slot straight into the v4
harness and the comparison is clean. Confirmed to exist on HF 2026-09-17 (repo names exact).

| priority | repo | what it is | why test it |
|---|---|---|---|
| **1** | `peculiar-ragdoll/Tiel-Coder-35B-A3B-GGUF-MTP` | Tiel + a **now-trained** multi-token-prediction head | v4 measured only the non-MTP Q5. The card says the MTP head was untrained when v4's tier was cut and was fixed 2026-08-23. Speculative decoding could move generation past the Q5 111 tok/s — pull `UD-Q5_K_XL`, measure against the v4 Tiel numbers head to head |
| **2** | `peculiar-ragdoll/Dirk-Qwen3.8-27B-GGUF` | Qwen3.8-27B with max-effort reasoning **removed** (terse, native medium) | v4 rejected `qwen3.8:27b` for being 4.3× slower — but that was with full thinking. Dirk is the "thinking-off by construction" build; it directly tests whether v4's `<\|think_off\|>` 2.3× finding generalises to a dense 27B. Dense, so expect ~30 tok/s base |
| 3 | `peculiar-ragdoll/Nail-Qwen3.6-35B-A3B-GGUF` | the "exam/knowledge" sibling — Tiel's card says +10.3 MMLU-Pro, −6.7 conversation | the knowledge-vs-coding trade, quantified. Likely loses the coding sessions but useful as the "generalist" data point |
| 4 | `peculiar-ragdoll/Cyber-Tiel-Coder-35B-A3B-GGUF-MTP` | abliterated Tiel + trained MTP head | only if the MTP head (#1) proves worthwhile; then this is its uncensored twin. Sandbox required |
| 5 | `peculiar-ragdoll/Occult-Nail-1.0-35B-A3B-GGUF` | a Nail variant (uncensored?) | low priority; verify what "Occult" means before spending a slot. Sandbox if abliterated |

Skip the MLX repos (`-MLX-*`) — `.67` runs Ollama/GGUF, not MLX.

## A2. Cross-vendor 35B-A3B on the Qwen3.6 base — verified 2026-09-17

Same `qwen35moe` architecture as Tiel, ornith and the control, so they slot into the harness
with zero changes and compare cleanly. Both confirmed on HF. **These are the strongest external
challengers** — a different team's post-training on the *identical* base the whole box is tuned
around, which isolates training from architecture.

| priority | source repo | GGUF (community) | what it is | why test it |
|---|---|---|---|---|
| **1** | `Kwaipilot/KAT-Coder-V2.5-Dev` | `bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF`, `mradermacher/…-i1-GGUF` | 35B-A3B coder on Qwen3.6, post-trained for "autonomous codebase manipulation, repo traversal, AST reasoning". Vendor claims ~69% SWE-bench Verified vs base ~64% | the closest direct competitor to Tiel that isn't a peculiar-ragdoll build. Apache-family, not abliterated, MTP + APEX GGUFs exist. Pull `Q5_K_XL`/`Q5_K_M` (~24 GB), measure head to head |
| **2** | `Accio-Lab/occamy-1.0` | `mradermacher/occamy-1.0-i1-GGUF`, `bartowski/Accio-Lab_occamy-1.0-GGUF` | Qwen3.6-35B-A3B derivative for **long-horizon co-work**, "Marathon + Sprint expert" merge. Vendor claims Claw-Eval 82.2 | tests the "co-work / multi-step" axis the hard fixture only samples. Q4≈20–24 GB fits. Claw-Eval is a vendor metric — verify against *our* sessions, do not quote theirs |

Vendor benchmark numbers above are **self-reported and on different harnesses** — record them as
claims, then measure on this box. That is the whole point of §8 of the harness.

## B. Ollama library / other vendors — new since the v3/v4 field

| priority | tag (VERIFY before pull) | what the web claims | fit? |
|---|---|---|---|
| **1** | `glm-4.7-flash` | newest 30B-class local coder, ~19 GB Q4, 198K ctx | **fits comfortably.** A different vendor's template is worth a gate run on its own — strongest non-Tiel candidate |
| 2 | `qwen3-coder:30b` | Qwen coder-specific MoE, 3B active, ~50% SWE-bench Verified, 4-bit fits a 24 GB card | fits; a coder-tuned Qwen distinct from the 3.6/3.8 generalists already tested |
| 3 | `devstral-small-2` (Mistral, 24B dense, 256K) | Mistral's agentic coder | fits, but **dense** → expect ~25–30 tok/s. One data point for "dense 24B vs 3B-active MoE" |

## C. Too big for this box — do not pull, noted so nobody tries

The 2026 frontier open coders are all far past 35.56 GB and are listed only to close the loop:

- **Kimi K2.7 Code** / **Kimi K3** (Moonshot) — K2-class is ~1T params
- **GLM-5.2** (the full model, not `-flash`)
- **DeepSeek V4**

These would need multi-GPU or heavy CPU spill; the box holds one ~30 GB model at a time.

---

## E. From the r/LocalLLaMA 35B-A3B tool-calling benchmark (read 2026-09-18)

Source: OsmanthusBloom's `tool-eval-bench 2.6.0` run, 13 GGUFs × 5 seeds on 32 GB V100s,
hardmode, 50 % context pressure. **It measures tool calling, not coding** — the author says so —
so it ranks candidates for us, it does not score them. Useful because it used 5 seeds and
published confidence intervals, which is more sampling discipline than most posts.

| reported | avg points | our read |
|---|---|---|
| Qwen3.8-27B | 152.6 | **already rejected here** — 30.3 tok/s, 4× slower than the field (§4c). Wrong shape for this box regardless of score |
| Ornith-1.5 | 144.2 | this *is* Tiel's base. We run the re-quant |
| Tiel-Coder | 144.0 | in the standing field |
| Qwen3.6-27B | 134.8 | **worth testing** — dense 27B, beats the 35B-A3B on tool calls, and unlike Qwen3.8-27B it is not automatically too slow. Check tok/s first |
| KAT-Coder-V2.5-Dev | 133.8 | already on the list (§A). CI overlaps the base Qwen — low priority |
| Ornith-1.5-Heretic | 132.2 | **skip.** The abliterated Ornith, and it lost to plain Ornith. Matches our CyberTiel result exactly: abliteration cost capability and bought nothing |
| Qwen3.6-35B-A3B | 131.5 | our control |

**Candidates this adds, in priority order:**

1. **`Qwen3.6-27B`** (dense). The one genuinely new signal: it beat the 35B-A3B on tool calling
   and it is the model the thread's most sceptical commenter says they keep using for real work.
   Gate on speed — dense 27B is the shape that sank Qwen3.8 here.
2. **`ManniX-ITA/OmniMerge` v4 and v6** (from the `mann1x` comment). A 27B merge on the Qwen3.6/3.8
   base; the author claims v4 finishes a job in 5–20 min where Ornith 27B needs 2 h 30. Claims are
   the author's own and uncontrolled — but "much faster at equal fix rate" is the axis this box
   cares about most, so it is worth one measured round.
3. **`Qwen3.6-35B-A3B` ByteShape CPU-5 quant.** Same model we already run, different quant, and it
   scored slightly above the Unsloth build. Cheap to test, and it would tell us whether our
   quant choice is leaving anything on the table.

**Explicitly not adding:** `Ornith-1.5-Heretic` (abliterated, lost to its base — we have that
result already), `Qwen-AgentWorld-35B-A3B` (the OP measured it at 121.0, ten points *below* the
base model), `BigBang` (one unsourced "I kinda liked it").

### What the thread is worth beyond the candidate list

- **`suprjami` posts Terminal-Bench 2.1 Terminus numbers**: Qwen3.8-27B 73.0, **Ornith-1.5 67.8**,
  Ornith-1.0 64.2, Qwen3.6-27B 63.4, **Qwen3.6-35B 52.5**, Muse Glimmer 51.7. Different harness
  version, different agent and an unknown subset, so the absolute numbers are not ours to quote —
  but the **ordering puts Ornith-1.5 fifteen points above Qwen3.6-35B, and our round found the
  reverse.** That contradiction is what led to finding our thinking asymmetry
  (`OFFICIAL_TB_PLAN.md`). Outside results are most useful exactly here: not as scores to copy,
  but as a check on whether our own ordering is believable.
- **The `peculiar-ragdoll` / `fragment_me` argument about whether a chat template can change
  capability** is directly relevant to us. The author's claim is that the Sharp template steers
  the model toward convergent thinking. If true, then *disabling thinking on a Sharp-template
  model removes the mechanism its advantage rests on* — which is precisely the error our round
  made. Their claim and our bug point at the same variable.
- **`suprjami` notes Tiel is Ornith re-quantized with a different template, not a fine-tune.**
  Consistent with `measurements.md`. Our own numbers are the useful evidence here: Tiel 41 % vs
  ornith 33 %, same direction as the author's SWE-Bench-Live claim, far smaller than his "50 %
  higher", and both at thinking parity only after the re-run.
- **Method to copy:** 5 seeds per configuration with published confidence intervals. We use n=3
  on the subject models and n=1 on comparators; the CI discipline is better than ours and it is
  cheap to adopt.

## F. Verified on the wire — what actually fits, 2026-09-21

Every row below was checked against the **Hugging Face tree API** (real file sizes, not card
claims) on 2026-09-21, and against the measured residency of this box: **35.56 GB usable, one
model resident, ~26 GiB of weights is the ceiling for a 262k window on the `qwen35moe` family**
(`plan.md` §8.1 has the KV arithmetic). Repo names in §E were approximate; these are exact.

| candidate | exact pull tag | GGUF | class | fit |
|---|---|---|---|---|
| ByteShape quant of our own control | `hf.co/byteshape/Qwen3.6-35B-A3B-GGUF:Q4_K_S-4.22bpw` | **17.02 GiB** file, 17.86 GiB pulled with the projector | M | **yes**, measured 2026-09-25: 28.53 GB resident against 32.68 GB, so ~4 GB lighter |
| Qwen3.6-27B dense | `hf.co/unsloth/Qwen3.6-27B-GGUF:Q5_K_M` | 18.17 GiB | D | yes on memory; **the speed gate is the question** |
| OmniMerge v4 | `hf.co/ManniX-ITA/Qwen3.6-27B-Omnimerge-v4-GGUF:Q5_K_M` | 17.91 GiB | D | yes on memory; same gate |
| OmniMerge v6 | `hf.co/mradermacher/Qwen3.8-27B-Omnimerge-v6-GGUF:Q5_K_M` | ~18.2 GiB | D | yes on memory; same gate. v6 is on the **Qwen3.8** base, v4 on 3.6 — they are not the same experiment |
| KAT-Coder-V2.5-Dev | `hf.co/bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF:Q5_K_M` | 23.30 GiB | M | yes, tight (~33 GB). Q4_K_M 19.92 GiB is the fallback if `/api/ps` shows a spill |
| occamy-1.0 | `hf.co/mradermacher/occamy-1.0-i1-GGUF:i1-Q4_K_M` | 19.71 GiB | M | yes |
| Tiel-Coder MTP | `hf.co/peculiar-ragdoll/Tiel-Coder-35B-A3B-GGUF-MTP:UD-Q5_K_XL` | 25.13 GiB | M | yes, at Tiel's own 1.4 GB margin |
| Nail-Qwen3.6-35B-A3B | `…/Nail-Qwen3.6-35B-A3B-GGUF:UD-Q5_K_XL` | 24.77 GiB | M | yes — the *exam* sibling, not a coder; low priority |
| Dirk-Qwen3.8-27B | `…/Dirk-Qwen3.8-27B-GGUF:UD-Q5_K_XL` | 19.44 GiB | D | yes on memory; dense, so the same gate as the others |
| **any Q8 27B, any Q6_K_XL 35B** | — | 26–30 GiB | — | **no.** Weights alone eat the KV budget |
| **ByteShape 3.48 / 3.80 / 3.93 bpw rungs** | — | 14–16 GiB | — | **no.** Below the 4-bit floor, standing rule |
| `-MLX-*` anything | — | — | — | **no.** `.67` runs Ollama/GGUF |

**MTP, on 0.33.3 — no longer settled.** Ollama honours the MTP head (`draft_num_predict 4`) and
v3 measured **+20% generation for −46% prefill**, a net loss when every turn re-read its
context. 0.33.3 caches prefixes, so that penalty is now paid roughly **once per session instead
of once per turn**. The `-MTP` builds are therefore a named experiment with a hypothesis, not a
default pull — and not the tag to reach for first.

**Dense 27B is the risk, and it is already quantified.** The class anchor on this box is
`qwen3.8:27b`: **30.3 tok/s, 787 s ledger median, 18/18 hidden ×3** — capable, four times too
slow. Qwen3.6-27B, both OmniMerges and Dirk are the same shape. They are worth the screen
because the OmniMerge claim is about *turn economy*, not tok/s (finishing in 5–20 min what
Ornith-27B needs 2 h 30 for), and turn economy is the axis this box actually feels — but the
gate is pre-registered in `plan.md` §8.3 and is not relaxed afterwards.

## F2. A wider sweep, 2026-09-21 — the class §E missed

§E's candidate list came from one reddit thread, and its top two picks were **dense 27B**, the
shape this box has already rejected once (`qwen3.8:27b`, 30.3 tok/s, 787 s ledger median). A
sweep of everything GGUF-quantized and coder-tagged since 2026-08 turned up a class the thread
did not mention and that fits far better: **27B-A3B MoE coders** — three billion active
parameters, coder post-training, and half the weights of our 35B field.

| candidate | tag | GGUF (Q5_K_M) | what it is |
|---|---|---|---|
| **Ornith-1.5-27B-A3B-Coder** / **-CoderX** | `hf.co/mradermacher/Ornith-1.5-27B-A3B-Coder-GGUF:Q5_K_M` | **17.44 GiB** | **Tiel's own base family, coder-tuned, at 27B.** The most interesting single candidate on this page: same lineage as the model holding slot 4, two-thirds the size |
| **Qwen3.6-27B-A3B-Coder** / **-CoderX** | `hf.co/mradermacher/Qwen3.6-27B-A3B-Coder-GGUF:Q5_K_M` | 17.44 GiB | coder post-training on the control's own base, MoE rather than dense — the honest version of §E's "Qwen3.6-27B" pick |
| KAT-Ornith-Coder-35B-A3B | `hf.co/mradermacher/KAT-Ornith-Coder-35B-A3B-GGUF:Q4_K_M` | 19.71 GiB (Q4_K_M) | a merge of the two strongest external lines we know of — KAT-Coder and Ornith |
| Qwen-35B-A3B-SignOfFour-Coder | `hf.co/pragmaticcs/Qwen-35B-A3B-SignOfFour-Coder-GGUF:Q4_K_M` | 20.00 GiB (Q4_K_M) | another 35B-A3B coder on the familiar base |
| LFM2.5-8B-A1B-Hermes-Agentic-Coder | — | ~5 GiB | 8B/A1B, abliterated. Far below the capability tier this box can host; noted only so it is not rediscovered |

**All of them fit comfortably** — 17–20 GiB of weights against a ~26 GiB ceiling, leaving room
for the full 262k window. The 27B-A3B pair fits with ~9 GiB to spare, which is the first
candidate class that could share the box with anything else.

**This re-orders §E.** The dense 27Bs (`Qwen3.6-27B`, `OmniMerge v4/v6`, `Dirk`) drop below the
A3B coders: same parameter budget, a quarter of the active parameters, and this box's one
measured data point on dense 27B is that it is four times too slow. They stay on the list —
OmniMerge's claim is about turn economy, not tok/s — but they are no longer the first pull.

**Revised pull order:** `Ornith-1.5-27B-A3B-Coder` (Tiel's family, small), then
`Qwen3.6-27B-A3B-Coder` (the control's family, small), then `KAT-Ornith-Coder-35B-A3B`, then
ByteShape (a quant question about a model we already run), then the dense 27Bs.

## The field a candidate is measured against — fixed 2026-09-18

A new contender is run against **four models and no others**: `qwen3.6:35b-a3b` (the control; the
2026-09-25 verdict in README.md names KAT-Coder, provisionally),
`north-mini-code-1.0` (speed ceiling), `gemma4:26b-a4b-it` (footprint floor and vision), and
`tiel-coder:35b-q5` (context safety). Each holds a different axis, and a candidate takes a slot
only by beating that slot's holder **on its own axis**.

CyberTiel, ornith, the shipped Tiel tag, nemotron-3.5-lightning, nemotron-cascade-2 and qwen3.8
are **retired from testing** — their numbers stay in the tables, they are not re-run. Roles,
reasons and the retirement list: `BENCHMARK_HARNESS.md` §9a.

Budget a candidate accordingly: five models total (candidate + four), **n ≥ 2** on anything the
recommendation will rest on.

## How to run one (from `BENCHMARK_HARNESS.md`)

```shell
# Stage 0 — identify before measuring
curl -s $H/api/pull  -d '{"model":"hf.co/<repo>:<QUANT>"}'      # or an ollama library tag
curl -s $H/api/show  -d '{"model":"<tag>"}'                     # quant, caps, TEMPLATE field

# Stage 1 — bake the deployable variant (num_ctx + presence_penalty 0)
curl -s $H/api/create -d '{"model":"<short>-ctx256k-agentic","from":"<tag>",
  "parameters":{"num_ctx":262144,"presence_penalty":0},"stream":false}'

# Stages 2-3 — the battery, then sessions (add gate-extra + dualuse for the full picture)
GATE_RUNS=3 NEEDLE_DEPTHS="2700 10700 40000 80000 110000 125000 135000" ./head2head.sh "$M"
python3 ./cache-probe.py "$M"; python3 ./overflow-probe.py "$M"; python3 ./gate-extra.py "$M"
./cc-session.sh --fixture hard --runs 3 "$M"          # sandboxed variant if abliterated
```

The bar to beat is **Tiel pp0**: 111 tok/s, holds 262,144 at 34.13 GB, recall 254,181, refuses
an over-long prompt, 18/18 held-out tests, 2.3× faster with `<\|think_off\|>`. A new model has to
win on **held-out correctness or safe overflow behaviour**, not just tok/s — see the harness §1.
