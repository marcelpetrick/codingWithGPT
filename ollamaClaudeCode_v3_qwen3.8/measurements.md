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

## 2. Throughput, gates and retrieval

*Running. Results land here.*
