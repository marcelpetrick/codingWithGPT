# Which local model should drive Claude Code?

Measured on **`192.168.100.67`** (Ollama 0.32.9, ~40 GB stated / **≈35.5 GB actually
usable**), 2026-08-11 → 2026-08-13. Server idle before every measurement, one model
resident at a time.

The `results/*.tsv` and `*.txt` files hold the raw data; `muse_ollama.md` holds the full
argument. This is the summary.

---

## The verdict

**Use `qwen3.6:35b-a3b-mtp-q4_K_M-agentic` at `num_ctx 262144`.**

| # | model | why, in one line |
|---|---|---|
| **1** | `qwen3.6:35b-a3b-mtp-q4_K_M-agentic` @ 262144 | 129 tok/s at the full native window for only 28.89 GB — best speed per GB on the box |
| **2** | `qwen3.6:35b-a3b-q4_K_M-agentic` @ 262144 | same speed (131 tok/s), 3.65 GB heavier, but no `draft_num_predict 0` override to depend on |
| **3** | `nemotron-3.5-lightning:30b-ctx512k-agentic` @ 524288 | the only model that stays 100% GPU-resident past 262k tokens, at 2.9× the cost in speed |

Shell aliases are wired for the top two: `claude-ol2` and `claude-ol-nemo`
(see [`shell_aliases.md`](shell_aliases.md)).

## The five models, measured identically

| | 35b-a3b *(incumbent)* | 35b-a3b-**mtp** | 27b-**q8_0** | **muse-glimmer** | **nemotron** |
|---|---|---|---|---|---|
| architecture | MoE, 3B active | MoE + MTP head | dense | dense | Mamba-2 + MoE |
| **generation** | **131.4 tok/s** | **129.0 tok/s** | 18.1 tok/s | 28.9 tok/s | 44.9 tok/s |
| **prefill** (35k) | **3,988 tok/s** | 3,369 tok/s | 1,464 tok/s | 1,963 tok/s | 3,050 tok/s |
| resident | 32.54 GB | **28.89 GB** | 34.03 GB | **19.45 GB** | 31.21 GB |
| **max ctx @ 100% GPU** | 262144 | 262144 | **81920** | 131072 | **524288** |
| tool gates T1–T5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| needle, same document | **PASS** | **PASS** | FAIL — window | **PASS** | **PASS** |
| vision | **yes** | yes | yes | yes | no |

**All five pass every tool gate.** Any of them works as a Claude Code driver; the choice
is speed, window and vision — not capability.

## What actually matters, in order

**1. Bake `num_ctx` into a Modelfile variant. Never use a bare tag.**
`/v1/messages` has no `num_ctx` knob, so a bare tag inherits a **16,384** default: past
it the prompt tail is discarded and **tool calling stops entirely, with no error**.
8 of the 23 tags on `.67` are bare.

**2. Overflowing a baked window silently costs you half of it.**
Confirmed at four different window sizes: 32768→16,387, 61440→30,002, 81920→40,962,
488192→244,098. Exactly half, every time, with `tool_use` dropped. A **1% overshoot
costs 50% of your context.** This is why the aliases set
`CLAUDE_CODE_MAX_CONTEXT_TOKENS` well below the baked window.

**3. Truncation is invisible *and* the model will make something up.**
On truncated runs Nemotron did not report failure — it invented a plausible passphrase
(`deploy-passphrase-2024`). No error, no refusal, no signal. Silent truncation plus
confabulation is the worst failure mode on this box.

**4. `presence_penalty 1.5` costs 31–35% of throughput — and 15 of 23 tags have it.**
The vendor default. Setting it to 0 is free performance; only the `-agentic` variants
clear it.

**5. MTP speculative decoding is a net loss here.**
`draft_num_predict`: 0 → 129.2 tok/s, 2 → 105.1, **4 (shipped default) → 100.6**,
8 → 58.9. It nearly halves prefill the moment it is enabled. Our variant bakes **0**.

**6. The box has ≈35.5 GB usable, not 40.4 GB.**
Measured: at `num_ctx 131072` the q8_0 asked for 38.33 GB and only 35.56 GB stayed
resident. The Ollama API exposes **no** VRAM field at all, so 40.4 was always a
human-supplied number. Roughly 5 GB of it is not spendable.

## What we got wrong, and corrected

Recorded because the corrections changed the recommendation:

- **"The incumbent fails at 120k"** — wrong. That datum belonged to `27b-q4_K_M`, a
  different model. The incumbent passes at **146,957 tokens**.
- **"Only Muse Glimmer has vision"** — wrong. Every `qwen3.6` tag does, and the
  incumbent is **4.5× faster** at it and read more out of the same screenshot.
- **Needle depths are not comparable across models.** All models got the *same*
  document; Nemotron's deeper token count is a **less efficient tokenizer** (+38%), not
  better retrieval.
- **Muse Glimmer is therefore not recommended** — slower than the incumbent, half the
  window, loses the vision comparison it was recommended for, and its advertised `xhigh`
  reasoning level is rejected by Ollama (three levels exist, not four).
- **`num_predict 64` in v1's needle harness manufactures failures.** Muse needs 70
  tokens to emit the passphrase. Use `needle-v2.sh`.

## Reproducing

```shell
./idle.sh       --host 192.168.100.67          # assert the server is empty first
./head2head.sh  --host 192.168.100.67 <model>  # throughput, residency, gates, needle
./tokrate.sh    --host 192.168.100.67 <model>  # tok/s only
./kv-probe.sh   --host 192.168.100.67 --model <model> --ctxs "..."
./cliff-probe.sh --host 192.168.100.67 <bare-tag> <baked-tag>
./needle-v2.sh  --host 192.168.100.67 --model <model> [--depths "..."]
```

`head2head.sh` calls `idle.sh` between **every** stage and aborts rather than benchmark
into a busy server: 19 GB + 31 GB will not co-reside in ~35.5 GB, and a 12.5% spill was
measured at **5.3× slower** — larger than the real difference between any two models
here, so a co-resident run produces a confident *wrong* answer rather than an obviously
broken one.

`.67` is **shared**. `idle.sh` only unloads models this project owns; anything else it
waits out rather than evicting.

## Files

| file | what it is |
|---|---|
| `muse_ollama.md` | the full document — architecture, budgets, every measurement, §9 methodology, §10 inventory, §11 the five-model comparison and corrections |
| `shell_aliases.md` | every `claude-ol*` alias and the measured reason for each setting |
| `results/tokrate.tsv` | all throughput rows, machine-readable |
| `results/h2h-*.log` | full battery transcripts |
| `results/inventory-67.txt` | all 23 tags with baked params and capabilities |
