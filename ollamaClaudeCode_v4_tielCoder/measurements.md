# v4 measurements

Everything on `192.168.100.67`, **Ollama 0.33.3**, ≈35.56 GB usable VRAM, server asserted idle
before every stage, one model resident at a time. Raw data in `results/`, reproducibility block
in [`results/provenance.txt`](results/provenance.txt), harness self-review in
[`review.md`](review.md). Written as the runs land; the verdict lives in `README.md`.

> **The runtime moved again, and this time it changed the rules, not just the numbers.**
> v3 measured 0.32.15. `.67` now runs **0.33.3**, which does **incremental prefix caching** —
> see §2. Every v3 speed number and every v3 session wall-clock is therefore non-comparable
> with what is below, and v3's ranking rule "prefill beats generation, you pay it every turn"
> does not survive.

---

# Stage S1 — Tiel-Coder, measured

## 1. What it is

`Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest`, on the box since 2026-09-14, manifest digest
`69b0f495f63e73c5`, 27.50 GB.

**It is not a fine-tune.** The card is explicit: this is
[Ornith-1.5-35B-A3B](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B) **re-quantized**
(Unsloth Dynamic + the publisher's own imatrix) carrying the "Sharp" chat template. The weights
are Ornith-1.5's. That makes v3's `ornith:35b` — Ornith **1.0**, q4 — the natural control, and
the comparison mostly measures *a generation of base model + a quant tier + a template*, not a
new training run.

```
family qwen35moe · 34.7B · Q5_K_M (UD-Q5_K_XL) · 262,144 native
block_count 40 · expert_count 256 · expert_used_count 8 · full_attention_interval 4
attention.head_count 16 · head_count_kv 2 · key_length/value_length 256
capabilities: tools, thinking, completion, vision (447M qwen3vl_merger projector)
shipped params: temperature 0.6 · top_k 20 · top_p 0.95 · min_p 0 · num_ctx 262144
                presence_penalty 1.5   <- see §6
```

**Two `/api/show` traps worth recording**, both new to this project:

1. **The Modelfile's printed `TEMPLATE` is not the template that runs.** `ollama show` prints a
   short Go template with no tool handling and a forced empty `<think></think>`. The `template`
   field is a 30,505-character **Jinja** template (`qwen3.8-froggeric-v22.5.0`, XML tool
   format), and that is what executes — proven because thinking appears and tool calls parse.
   Reading the Modelfile alone would have predicted "no tool support" and been wrong.
2. **`presence_penalty 1.5` is in the tag, not in the model.** The raw download
   `hf.co/peculiar-ragdoll/Tiel-Coder-35B-A3B-GGUF:UD-Q5_K_XL` ships **no** parameters beyond
   stop strings. The penalty, the 262,144 window and `temperature 0.6` were all added by
   whoever created the `-ctx262k` tag on 2026-09-14. The vendor card recommends
   `temperature 0.6, top_p 0.95, top_k 20` for agentic coding and **no presence penalty at
   all**. §6 measures what it costs.

The quant tier is one step **above** the vendor's own benchmarked tier: the card's SWE-bench-Live
and Claw-Eval numbers are UD-Q4_K_XL; the box has UD-Q5_K_XL.

## 2. The runtime caches prompts now — and it invalidates a v3 rule

Found while checking an anomaly: the T7 gate printed "3/3 at **4** tokens" for what should be a
53k-token context. The harness was reading only `usage.input_tokens`; 0.33.3 splits the prompt
into `input_tokens` (freshly prefilled) and `cache_read_input_tokens` (served from cache).

`cache-probe.py`, Tiel Q5, unique 30k-token prompts, thinking disabled:

| request | prefilled | from cache | wall | implied |
|---|---|---|---|---|
| cold, unique prompt | 30,042 | 178 | 7.85 s | 3,848 tok/s |
| **the identical prompt again** | **4** | 30,216 | **0.64 s** | 47,114 tok/s |
| **same prefix + a new tail** | **517** | 29,708 | 0.94 s | 32,149 tok/s |
| a different unique prompt | 30,045 | 178 | 8.31 s | 3,637 tok/s |

**Every v3 gate response and every v3 session transcript reports `cache_read = 0`.** On
0.32.15 there was no prefix cache; on 0.33.3 there is, and it is incremental — row 3 is the
shape of an agent turn (a long stable prefix with a tool result appended), and it prefills only
the tail.

Consequences, written down before the field was measured:

1. **v3's rule "prefill beats generation for this workload, because the loop re-reads its
   context every turn" is suspended.** It described a runtime that no longer exists here. Cold
   prefill now sets the cost of the *first* turn; after that, generation speed and turn count
   dominate.
2. Session wall-clocks are not comparable across 0.32.15 → 0.33.3, on top of the throughput
   re-ranking v3 already documented.
3. Both numbers are reported per model from here on: **cold** prefill (`tokrate`, unique
   prompts) and **warm/incremental** prefill (`cache-probe`).

## 3. Memory — it fits, with 1.43 GB to spare

`kv-probe.sh`, ladder at 100% GPU throughout:

| num_ctx | resident | % GPU |
|---|---|---|
| 65,536 | 29.270 GB | 100% |
| 131,072 | 30.369 GB | 100% |
| **262,144** | **34.127 GB** | **100%** |

Marginal KV cost is **16,765 B/token** between the first two rungs and **28,672** between the
last two — not constant, the same allocation-regime effect v3 saw on north-mini and gemma4, so
no single slope is quoted. Averaged across the ladder it is 24,704 B/token, against 20,480
predicted from `(40/4) × 2 × 2 kv-heads × 256 × 2 B` — `full_attention_interval 4` is honoured,
as it was for Qwen3.8 and ornith.

**34.13 GB of a 35.56 GB ceiling is the tightest fit in the project** — 1.43 GB of headroom,
against north-mini's 14.2 GB. It holds, including with an image workspace (§7), but nothing
else can be resident beside it.

## 4. Throughput — the Q5 tier costs what you would expect

`tokrate.sh`, temperature 0, seed 42, think:false, `num_predict` 256, cold prompts:

| prompt | prompt tok | prefill tok/s | generation tok/s |
|---|---|---|---|
| empty | 203 | 429 | 72.58 |
| 2,000 words | 3,358 | 2,805 | **73.16** |
| 20,000 words | 35,280 | **3,548** | 69.41 |

That is the shipped tag, i.e. **with `presence_penalty 1.5`**. §6 is the same table without it.

## 5. Gates and retrieval — clean, and the deepest retrieval ever measured here

**T1–T7, three full batteries: 10/10, 10/10, 10/10.** Including T4 (parallel calls) and T5
(nested schema), the two that broke `nemotron-cascade-2` in v3.

One honest correction to that, from §8: re-running **T5 alone eight times gives 7/8** — the
battery's three clean sweeps were partly luck. See §8; it is flakiness, not a defect, and it is
not caused by the presence penalty.

`needle-v2.sh`, `--num-predict 2048`:

| depth (words) | prompt_eval | verdict |
|---|---|---|
| 2,700 | 4,589 | PASS |
| 10,700 | 18,039 | PASS |
| 40,000 | 72,597 | PASS |
| 80,000 | 147,135 | PASS |
| 110,000 | 203,039 | PASS |
| 125,000 | 233,729 | PASS |
| **135,000** | **254,181** | **PASS** |

**254,181 tokens verified — the deepest in v1–v4**, past ornith's 254,061, at **97.0% of its
baked window**. It passed every rung on the first attempt and the ladder never found a failure,
so this is a floor on its retrieval, not a ceiling. §9 pushes further.

## 6. `presence_penalty 1.5` costs ~35% of generation, and nothing else

The tag ships it; the vendor card does not recommend it; v1 measured 1.5 as costing ~35% of
throughput on a Qwen MoE. `tiel-coder:35b-q5-ctx256k-agentic` is the same weights with
`presence_penalty 0` and nothing else changed (it shares the blob, so it cost 0 bytes of disk):

| prompt | | shipped (1.5) | variant (0) | delta |
|---|---|---|---|---|
| empty | generation | 72.58 | **107.08** | **+47.5%** |
| 2,000 words | generation | 73.16 | **111.13** | **+51.9%** |
| 20,000 words | generation | 69.41 | **97.64** | **+40.7%** |
| 2,000 words | prefill | 2,805 | 2,772 | −1.2% |
| 20,000 words | prefill | 3,548 | 3,483 | −1.8% |

**Generation +41% to +52%; prefill unchanged within noise.** v1's finding reproduces on 0.33.3
on a different model family: the penalty is paid per generated token, in the sampler, and the
prefill path never touches it.

It costs nothing in capability either — the variant scores the same 25/25 vision (§7), the same
needle depths, and the same 7/8 on a T5 re-run (§8). Plan rule 5 fires: **the recommended tag is
the `presence_penalty 0` variant.**

## 7. Vision — 25/25, at the full window

`vision-bench.py`, the three fixtures and 25 objective checks from
`../ollamaClaude_ImageProcessing`, `think:false`, **at the baked 262,144 window**:

| tag | invoice OCR | UI description | chart extraction | total | thinking chars |
|---|---|---|---|---|---|
| shipped (pp 1.5) | 9/9 | 6/6 | 10/10 | **25/25** | 0 |
| variant (pp 0) | 9/9 | 6/6 | 10/10 | **25/25** | 0 |

Two things this settles:

- **`think:false` is honoured** on `/api/chat` for these tags (0 thinking characters), unlike
  `qwen3-vl:32b`, which ignored it and needed a `/no_think` prompt prefix.
- **The image workspace fits in the 1.43 GB of headroom.** `qwen3-vl:32b` loaded fine at 53,248
  and then returned HTTP 500 on its first image, which is why that study had to drop to a
  49k-token tag. Tiel reads images **at 262,144** with 34.13 GB resident and no error. It is the
  only model in this project verified to do OCR at a quarter-million-token window.

Generation during vision tracks §6: 75–78 tok/s shipped, 109–112 tok/s on the variant.
