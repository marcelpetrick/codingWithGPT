# Benchmark plan — Ollama v1 (new server 192.168.100.67)

Status: **planning only. Nothing measured yet.** Written 2026-08-04.

---

## 0. Current state

| Item | State |
|---|---|
| `ollamaClaudeCode_v0/` | Old dir, renamed from `ollamaClaudeCode/`. Rename **not committed** (git shows deletes + untracked dir). |
| `ollamaClaudeCode_v1/` | Empty except this file. |
| Old server `192.168.100.37` | **Unreachable from this machine.** |
| New server `192.168.100.67` | **Unreachable from this machine.** |

Verified 2026-08-04, outside the sandbox:

```
192.168.100.37: no ICMP reply    192.168.100.37:11434 unreachable
192.168.100.67: no ICMP reply    192.168.100.67:11434 unreachable
```

This laptop sits on `10.185.212.209/8` (wlp0s20f3), default route `10.128.128.128`.
There is no route to `192.168.100.0/24`. **This is a hard blocker for every
measurement phase below** — it is a network-location problem (VPN / on-site /
SSH jump host), not something that can be worked around locally.

Local Ollama (`localhost:11434`, v0.31.2) is alive but only holds 4b-class models —
usable to dry-run the harness script, not to produce any comparable numbers.

---

## 1. The core problem: two different benchmarks are being compared

The numbers pasted from Alex are **not** from `v0/benchmark.sh`. They are a
different workload, so putting them in one table would be wrong.

| | Repo benchmark (`v0/benchmark.sh`) | Alex's run |
|---|---|---|
| Invocation | `POST /api/generate`, `stream:false` | `ollama run --verbose` (CLI) |
| Prompt | Sieve of Eratosthenes, type hints + docstring | "Write exactly 1000 tokens about GPUs." |
| Output cap | `num_predict: 300` | uncapped (828 / 2889 tokens observed) |
| Task type | code | prose |
| Timeout | 180 s | none |

Why this matters: `eval rate` is not invariant to generation length. A run capped
at 300 tokens carries a larger share of warm-up per token than a 2889-token run,
so the two systematically disagree. v0's `qwen3.5:9b` at 46 tok/s and Alex's
`llama3.1:8b` at 86.9 tok/s are **not** a like-for-like 2x — part of that gap is
hardware, part is methodology, and right now we cannot say how much is which.

**Decision baked into this plan:** the v1 harness runs *both* profiles against
every model under test:

- **Profile S (short/coding)** — identical to `v0/benchmark.sh` (sieve, 300 tokens).
  Keeps continuity with runs 1–5 in `v0/README.md`.
- **Profile L (long/prose)** — Alex's prompt, uncapped (hard ceiling `num_predict:
  4096` as a runaway guard). Makes our numbers directly comparable to his.

Every reported figure is tagged S or L. They are never averaged.

---

## 2. What we do not know about the new server

Alex's numbers imply a substantially stronger machine than `.37` (a 27–36b-class
model at ~90 tok/s, where `.37` did 46 tok/s on a 9b and went split-VRAM above
~12.2 GB). But we have no fingerprint. Before any benchmark, `.67` must be
characterised:

- Ollama version
- GPU model, VRAM total, driver
- installed model list (`/api/tags`)
- what is already resident (`/api/ps`) and who else is using the box

**Consequence:** the v0 finding "ctx80k is the sweet spot" is a property of a
12 GB GPU. It does **not** transfer to `.67`. A fresh context sweep is required
there (Phase 5) — carrying the 80k number over would be a mistake.

The note "256K Context als Standard" needs verification: is that a server-side
`OLLAMA_CONTEXT_LENGTH`, or per-model `num_ctx`? It changes KV-cache footprint
enormously and would silently distort every result if left unknown.

---

## 3. Known trap: thinking mode

This already burned run 5 in v0 and it burned Alex too — same failure, twice:

| Source | Model | Result |
|---|---|---|
| v0 run 5 | `qwen3.5:27b` | 0 tok/s — "thinking consumes all tokens" |
| v0 run 5 | `qwen3.6:27b-q4_K_M` | 0 tok/s — same |
| Alex, `.67` | `qwen3.6:27b-q8_0` | "denkt ewig nach — das thinking nimmt kein Ende" |

Interesting counter-example: Alex's `qwen3.6:36b-q4_K_M` **did** finish (2889
tokens, 89.8 tok/s). So this is not simply "big model = hangs". It is likely
quantisation/variant-specific thinking behaviour, or a `num_predict` cap being
consumed entirely by the reasoning block.

Phase 4 must therefore treat thinking as a measured variable, not an obstacle:

1. Re-run with `"think": false` in the `/api/generate` options.
2. Re-run with `/no_think` appended to the prompt (older Qwen convention).
3. Re-run uncapped with a long timeout (600 s) to see whether it *ever* terminates.
4. Where the API exposes it, count thinking tokens separately from answer tokens.

A model that only produces an answer with thinking disabled gets reported as such.
Reporting "0 tok/s" again without distinguishing these cases would repeat v0's
mistake of recording a symptom instead of a cause.

---

## 4. Care items — `.67` is not our box

Alex owns/shares it. Everything below is written to avoid disrupting them.

- **Get explicit permission before a full sweep.** A one-model probe is fine;
  iterating 20 models and pulling new weights is not something to start unasked.
- **Serialize, and unload between models.** v0 run 3 lost an entire run to a
  model-swap deadlock: a cold 22b load exceeded the 180 s timeout, left Ollama
  mid-swap, and every later request queued behind it. Mitigation: after each
  model, issue a `keep_alive: 0` request and poll `/api/ps` until VRAM is free
  before touching the next one.
- **Raise the timeout for first touch.** 180 s is too short for a cold 27–36b
  load. Use 600 s on first contact with a model, 180 s once it is warm.
- **Have a recovery path agreed in advance.** If the queue deadlocks, the fix is
  `systemctl restart ollama` on the server. Confirm *before starting* whether we
  have that access or whether Alex is on standby — otherwise a deadlock leaves
  their machine broken and us unable to fix it.
- **Do not pull large models without asking.** `qwen3.6:36b-q4_K_M` and
  `27b-q8_0` are tens of GB of their disk and bandwidth.
- **Check `/api/ps` for other users' load first.** Benchmarking on top of
  somebody else's active session produces garbage numbers and steals their VRAM.

---

## 5. Phases

Each phase states its precondition, so nothing starts before the ground for it
exists. Phases 1–7 are all blocked on Phase 0.

### Phase 0 — connectivity (user action, blocking)

Get this machine onto a network with a route to `192.168.100.0/24` — VPN, on-site
wifi, or an SSH tunnel (`ssh -L 11434:192.168.100.67:11434 <jumphost>`, then point
the harness at `localhost:11434`). Nothing else can proceed.

Exit criterion: `curl http://192.168.100.67:11434/api/version` returns a version.

### Phase 1 — fingerprint both servers (read-only, ~2 min, safe)

`/api/version`, `/api/tags`, `/api/ps` on `.37` and `.67`. Record GPU/VRAM from
whoever has shell access. No inference. Output: `plan.md` → `serverinfo.md`.

Risk: none. Can run the moment Phase 0 clears.

### Phase 2 — reproduce the v0 baseline on `.37`

Run harness v1 (Profiles S **and** L) against `.37`. Purpose: confirm the old box
still behaves as in run 5, and calibrate the S-vs-L delta on hardware we already
have five runs of history for. That delta is what lets us later separate
"different machine" from "different prompt" in Alex's numbers.

Precondition: `.37` still exists and is ours to hammer. **Open question — is `.37`
still in service, or has it been replaced by `.67`?** If retired, this phase is
dropped and the S/L calibration moves to `.67`.

### Phase 3 — `qwen3.5:9b-ctx80k` on `.67` (the direct ask)

Same model, same two profiles, new hardware. This is the clean
old-server-vs-new-server comparison.

Precondition: the model exists on `.67`. If not, it needs a pull + a Modelfile
(`PARAMETER num_ctx 81920`) — that is a write to their machine, so ask first.
Note the `ctx80k` figure is inherited from a 12 GB GPU and is used here only to
hold the variable constant, not as a recommendation for `.67`.

### Phase 4 — bigger/newer Qwen models on `.67`

`qwen3.6:36b-q4_K_M`, `qwen3.6:27b-q8_0`, plus `llama3.1:8b` as the tie-in to
Alex's reference number. Apply the full thinking-mode protocol from §3 to the
27b/36b runs.

Only models **already present** on `.67` in the first pass. Pulling anything new
is a separate, explicitly-approved step.

### Phase 5 — context sweep on `.67`

Re-derive the VRAM ceiling for the winning model on the new GPU, the way v0 did
for `.37` (4k → 32k → 64k → 80k → 128k → 256k). Find where it stops fitting
fully in VRAM and speed falls off. This answers whether "256K als Standard" is
actually free or is quietly costing throughput.

Precondition: Phase 4 has picked a winner. Requires creating Modelfile variants
on their server → needs approval.

### Phase 6 — tool-use verification

Speed is worthless if Claude Code cannot drive the model. Run the `/v1/messages`
tool-use probe from `v0/OLLAMA_PULL.md` against every candidate that survived
Phases 3–5. Expect `stop_reason: tool_use` + a `tool_use` block.

v0 evidence: `qwen3.5` family and `mistral-nemo` pass; `qwen2.5-coder` and
`codestral` fail. The `qwen3.6` family is **untested** for this — and it is the
single most likely reason a fast model turns out unusable.

### Phase 7 — write up

`ollamaClaudeCode_v1/README.md`: server info, S and L result tables, thinking-mode
findings, context sweep, tool-use matrix, updated `claude-ol*` aliases pointing at
`.67`. Commit the `v0` rename together with the new `v1` content so the history
shows one coherent move.

---

## 6. Deliverables

| File | Content |
|---|---|
| `plan.md` | this file |
| `benchmark.sh` | harness v1 — S+L profiles, configurable host, `keep_alive:0` unload between models, per-model timeout tiers |
| `serverinfo.md` | Phase 1 fingerprints |
| `README.md` | final results + recommendation + aliases |

The harness is a rewrite of `v0/benchmark.sh`, not a copy. Changes needed:
`SERVER` as a parameter instead of a hardcoded IP, two prompt profiles, forced
unload between models, tiered timeouts (600 s cold / 180 s warm), thinking-token
accounting, and machine-readable output (JSON/TSV) so runs can be diffed instead
of eyeballed.

---

## 7. Open questions — need answers before scheduling

1. **When is there network access to `192.168.100.0/24`?** Everything waits on this.
2. **Is `.37` still alive?** Determines whether Phase 2 happens at all.
3. **How much freedom on `.67`?** Read-only probing / full sweep of existing
   models / permission to pull and create Modelfile variants — three very
   different levels of intrusion.
4. **Who can restart Ollama on `.67`** if the swap deadlock from v0 run 3 recurs?
5. **Commit the `v0` rename now, or once v1 has content?**

---

## 8. Sequencing proposal

| When | What | Needs |
|---|---|---|
| now, offline | write harness v1, dry-run against `localhost` 4b models | nothing |
| first network access | Phase 1 fingerprint | route to `.67` |
| same session | Phase 3 (single model, low impact) | model present on `.67` |
| after Alex's OK | Phases 2, 4 | permission + restart path |
| follow-up session | Phases 5, 6 | Modelfile write access |
| after results | Phase 7 | — |

The harness can be built and dry-run today. Nothing else can.
