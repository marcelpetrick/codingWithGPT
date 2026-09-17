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
