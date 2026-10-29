# PLAN: Magnitude versus Ollama

Living document. Started 2026-10-29.

## Verdict (2026-10-29, final for the laptop)

**Magnitude is faster only where it has a drafter that Ollama does not have.** The engine itself is not
faster at decode. Measured on an RTX A2000 8 GB laptop, 2026-10-29, fixed rule (n = 5, median ≥ 25% higher
and no range overlap):

| Model | Magnitude | Ollama | New code (B) decode | Rule verdict |
|---|---|---|---|---|
| **Gemma 4 E4B** QAT Q4 (fills the 8 GB) | MTP drafter, 48–51 tok/s | no MTP tag, 25–28 tok/s | **1.81–1.88x** | **Magnitude better** |
| Qwen3.5 2B Q4_K_M | no drafter offered, 50–53 tok/s | plain tag, 50–52 tok/s | 0.99–1.02x | tie |
| Qwen3.5 2B Q4_K_M | no drafter offered, 50–53 tok/s | MTP tag, 63–66 tok/s | 0.78–0.80x | **Ollama clearly faster** |
| Gemma 4 E2B QAT Q4 (quick test, n = 3) | MTP drafter, 58 tok/s | no MTP tag, 51 tok/s | 1.15x | tie |

- **Without a drafter, both engines decode at the same speed** (Qwen 2B: 0.98–1.02x; Gemma E4B on the one
  prompt where Magnitude did not draft: 24.6 vs 25–29 tok/s).
- **Prefill** is often faster on Magnitude (1.1–1.4x with long prompts), but mostly within the tie band.
- **The vendor's repeat task inflates the gain**: 3.0x (E4B, 16k) and 5.4x (E2B, 4k), against 1.8x on new code.
- **Magnitude's drafter is prompt-dependent**: on one 3.2k-token prompt it did not draft at all (reproduced).
- **Quality and vision are kept**: C 19/20 vs 17/20 (E4B), 14/20 vs 12/20 (Qwen 2B); V 5/5 vs 5/5 and 4/5 vs 4/5. All ties.
- **Fit is worse on 8 GB**: Magnitude plans for the full 256K context and refuses Qwen3.5 4B, which Ollama
  runs in 3.7 GB. Qwen3 / Qwen3-VL have no Magnitude kernels. Qwen3.6 35B does not fit (no MoE offload).
- **Not a drop-in for the Ollama API** (see below). Claude Code works through `/inference/anthropic` (smoke test: one tool call, 25 s).

Details: `report.md`, `dashboard.html`, `README.md`. Earlier gate notes (still valid):

1. Magnitude 0.2.14 installs and runs here (CUDA on the A2000).
2. Qwen3.6 35B-A3B: blocked (24.2 GB, no MoE expert offload, issue #194).
3. Qwen3.5 4B: refused (256K-context planning, 212 MB short even when forced).
4. Correction: the E4B A-4k rows were first excluded as "kernel tuning after the first load". The
   re-measurement after a stable warm-up gave the same 24.6 tok/s: Magnitude does not draft on that
   prompt. The first diagnosis was wrong; `results/exclusions.jsonl` says so.

## Prediction for the box `.67` (written 2026-10-29, before any box data)

Basis: the laptop round (engine alone about 1.0x; the drafter decides; the repeat test inflates the gain
about 1.7x against new code) and the box notes (about 35.5 GB usable, GPU model and count unknown;
current Qwen3.6 tag `qwen3.6:35b-a3b-q4_K_M-agentic-t06` without MTP, 131–136 tok/s; default model
KAT-Coder-V2.5 Q5_K_M, a Qwen3.6 fine-tune). Ollama has `qwen3.6:35b-a3b-mtp-q4_K_M` and
`qwen3.6:35b-a3b-coding-mtp-q4_K_M` (23 GB each).

| Setup | Predicted decode on new code | Reason |
|---|---|---|
| Magnitude Qwen3.6 (DFlash) vs Ollama current tag (no MTP) | 1.5–2x, Magnitude clearly faster | drafter against no drafter |
| Magnitude Qwen3.6 (DFlash) vs Ollama `…-mtp-q4_K_M` | 1.2–1.5x, often a tie under the 25% rule | DFlash against MTP |
| KAT-Coder on both | tie | probably no drafter on either side for the fine-tune |
| Prefill | about 1.1x, tie | vendor 1.11x for Qwen3.6; laptop 1.1–1.4x |
| Tuned kernels alone (MoE, 3B active) | 1.0–1.15x | laptop: no decode gain without drafters; MoE has many small expert matmuls, where tuning can help a little more |

Tuned kernels on the laptop: decode without drafters 0.98–1.02x (Qwen3.5 2B) and 24.6 vs 25–29 tok/s
(Gemma E4B, the prompt without drafting); prefill 1.1–1.4x with long prompts. Both engines hit the same
decode ceiling; the tuning did not move it.

Stoppers: more than one GPU (Magnitude issues #128, #141: second GPU not used); the 256K-context fit
plan (KAT at Q5 is tight). First check (about 10 minutes, needs the owner's approval for `.67`):
`magnitude hardware`, `magnitude catalog show qwen3.6-35b-a3b:gguf:q4`,
`magnitude catalog inspect bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF`.
Independent of Magnitude: measure Ollama's MTP tag against the current tag on `.67` (expected +25–40%).

## Is the claim false advertising? (owner question, 2026-10-29)

Not false, but framed too favorably. The gain is real where Magnitude has a drafter that Ollama lacks
(Gemma 4 E4B: 1.8x on new code). The engine alone is not faster (0.98–1.02x). Where Ollama has the
better drafter (Qwen3.5 2B MTP), Ollama is faster. The vendor used one best-case prompt, Ollama 0.35.1
and n = 2.

Agentic coding, estimates (not measured):

- Prefill runs on every request, but only for the new tokens (both engines cache the prefix). One agent
  turn on `.67`: about 5k new tokens prefill (about 2.5 s) and about 300 tokens decode (about 2.3 s).
  A 1.1x prefill gain saves about 5% of a turn.
- Agents copy a lot (Edit `old_string`/`new_string`, file rewrites, tool-call JSON), so drafters help more
  than on new code. Expected E4B gain for agentic coding: between B (1.8x) and A (3.0x), about 2–2.5x.

## Open decisions (owner decides later)

| # | Option | Effort | Value |
|---|---|---|---|
| 1 | On `.67`, without Magnitude: Ollama `qwen3.6:35b-a3b-mtp-q4_K_M` vs the current tag | about 30 min | expected +25–40% decode, no new software |
| 2 | On `.67`: install Magnitude (no server mode), run `magnitude hardware`, `catalog show qwen3.6-35b-a3b:gguf:q4`, `catalog inspect bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF` | about 10 min, needs approval (shared box) | settles GPU count, fit and drafter |
| 3 | If 2 looks good: one real Claude Code session (ledger task) on each engine | about 1 h | answers the agentic question directly |
| 4 | Workload E (edit an existing file) on the laptop | about 30 min | refines the agentic estimate; low priority |
| 5 | Magnitude on the laptop: keep or remove (`magnitude server remove`, `sudo pacman -R magnitude-desktop`) | 2 min | it runs at boot on `0.0.0.0:10100` |
| 6 | Push the commits | 1 min | CI run, Pages build check |

## Vendor claim, and why it is weak

Source: https://magnitude.dev/benchmarks (read 2026-10-29).

| Point | Vendor setup | Problem |
|---|---|---|
| Ollama version | 0.35.1 | Old. Local is 0.40.4, the box is 0.40.11. |
| Workload | One 64k prompt: "repeat the latest Moby-Dick passage" | Repeating known text is the best case for speculative decoding. The drafter guesses almost every token. |
| Drafter | Ollama: MTP of the tag. Magnitude: own DFlash. | The speed-up is mostly the drafter, not the kernel tuning. |
| Context | 64k only | No data for short prompts (normal chat, agent turns). |
| n | Median of 2, some Ollama rows n=1 | n=1 is not a result. |
| Quality | Not scored | Different weights, templates and numerics. |
| Hardware | M4 Pro 48 GB, DGX Spark 128 GB | No small discrete GPU. |
| Qwen3.6 35B on DGX | decode 85.8 → 216 tok/s (2.52x), prefill 1.11x | Prefill gain is small. Decode gain needs a check on a non-repeat task. |

## Decision rule (fixed 2026-10-29, before any data)

1. Measure decode tok/s and prefill tok/s on the client side, n = 5 runs per cell, after 1 warm-up run.
2. "Clearly faster" = median ≥ 25% higher **and** the min–max ranges do not overlap.
3. Anything else is a **tie**.
4. Magnitude is "really better" here only if it is clearly faster on workload B (realistic coding)
   **and** it is not worse on quality (workload C: no task that Ollama passes and Magnitude fails
   more than the reverse, out of 20 tasks; a difference of ≤ 2 tasks is a tie).
5. A "does not load" or "refused" result is a valid result for "does it work here". It is never a speed number.

## Workloads

| ID | What | Why |
|---|---|---|
| A | Vendor replication: Moby-Dick text, repeat the latest passage, greedy, thinking off, 256 output tokens. Context 4k and 16k (64k does not fit 8 GB). | Check the vendor number on our hardware. |
| B | Realistic coding: 5 prompts that ask for new code (no copy), 512 output tokens, context 1k and 8k. | Speculative decoding helps less on new text. This is the real use. |
| C | Quality parity: 20 small Python tasks with unit tests, greedy, pass/fail. | Faster but wrong is not better. |
| D | Memory: largest context that loads, peak VRAM at load and during B. | 8 GB is the limit here. |

## Arms

| Arm | Engine | Drafter |
|---|---|---|
| `magnitude-default` | Magnitude, catalog default | MTP / DFlash of the catalog |
| `magnitude-nodraft` | Magnitude, drafter off (`--drafter none`) | none |
| `ollama-mtp` | Ollama, MTP tag where one exists | MTP |
| `ollama-plain` | Ollama, plain tag | none |

The `nodraft` and `plain` arms separate "kernel tuning" from "speculative decoding".
`magnitude-nodraft` vs `ollama-plain` is the clean engine-against-engine test.

## Install record (laptop)

- 2026-10-29: the owner ran `curl -fsSL https://magnitude.dev/install.sh | sh` and answered **yes** to
  server mode. The package `magnitude-desktop 0.2.14-64` (pacman) is installed.
- Effect: systemd unit `magnitude.service`, enabled at boot, listens on `0.0.0.0:10100` (all
  interfaces), protected by a network access key. The key is not stored in this repo.
- Confound: server mode updates itself. Every row records the engine version. Rows of two versions
  never pool.
- Models go to `/var/lib/magnitude` (owned by the service user). Magnitude cannot read the
  Ollama folder `/usr/share/ollama/.ollama/models`, so it cannot reuse the Ollama GGUF files.
- Remove after the round: `magnitude server remove`, then `sudo pacman -R magnitude-desktop`.
- An earlier user-space try (unpacked package, `magnitude serve`) failed with "installation
  admission is missing": the binary needs the root-owned `/var/lib/magnitude-desktop/installation.lock`.

## Sites and models

| Site | GPU | Model | Status |
|---|---|---|---|
| Laptop | RTX A2000 8 GB Laptop, sm_86, driver 610.57.04; i9-12900H; 33 GB RAM | Gemma 4 E2B QAT Q4 | Go (both engines allow it) |
| Laptop | same | Gemma 4 E4B QAT Q4 | Go if it loads (Magnitude lists 8 GB, the limit) |
| Laptop | same | Qwen3.5 4B Q4 | Gate only: Magnitude refuses it. Forced load is a test, not a match. |
| Box `192.168.100.67` | ~35.5 GB VRAM, Ollama 0.40.11 | Qwen3.6 35B-A3B Q4 | Blocked: needs owner approval to install Magnitude (shared box) |

### Overlap: Magnitude models that fit here, and Ollama

Magnitude lists 20 compatible models on this laptop (`magnitude catalog list`, 2026-10-29).
None of them is installed in the local Ollama. Only Gemma 4 has the same model and quant in the
Ollama library:

| Magnitude here | Ollama tag | Match |
|---|---|---|
| `gemma-4-e2b-it-qat:gguf:q4` (5.7 GB, MTP) | `gemma4:e2b-it-qat` (4.3 GB) | Same QAT weights. Ollama has no MTP tag for E2B. |
| `gemma-4-e4b-it-qat:gguf:q4` (8 GB, MTP) | `gemma4:e4b-it-qat` (6.1 GB) | Same. Borderline fit for Magnitude. |
| LFM2.5 / LFM3, MiniCPM5, MiniCPM-V 4.7 | not checked as same quant | Not used: no vendor number, no local use. |

### Earlier laptop numbers in this repo

None are usable as a baseline. `ollamaClaudeCode_v0` measured the network server, not this laptop.
`ollamaClaudeCode_v2/muse_ollama.md` ran a model split between GPU and CPU on this laptop.

## Focus: models that fill the 8 GB (owner, 2026-10-29 14:55)

Fit check with `magnitude catalog inspect` on this laptop:

| Model | Magnitude | Ollama | Use |
|---|---|---|---|
| Gemma 4 E4B QAT Q4 (8B with PLE) | "Snug (8 GB)", MTP drafter | `gemma4:e4b-it-qat` 6.1 GB, no MTP tag | **Main match: fills the GPU** |
| Qwen3.5 4B | refused (plans 256K ctx, 212 MB short even forced) | runs, 100% GPU | Gate result only |
| Qwen3.5 2B | fits (Q4_K_M to BF16), no drafter offered | `qwen3.5:2b` plain and MTP | Qwen match, pure engine |
| Qwen3 / Qwen3-VL (all sizes) | "No kernels for the qwen3 architecture" | runs | Not comparable |
| Gemma 4 E2B | fits, MTP | `gemma4:e2b-it-qat` | Quick test only (done) |

New workload **V** (vision kept?): 5 generated PNG images with known answers (shapes, count, tallest bar,
flag stripes, corner). Pass = every expected keyword matches. Images go as `images` (Ollama) or an
`image_url` data URI (OpenAI protocol).

Report fix: pairs now form only inside one model family (site, family, workload, ctx). Before, two
families on one site would have paired Magnitude-Gemma with Ollama-Qwen.

## Ollama API compatibility (owner question, 2026-10-29)

Magnitude is **not** a drop-in replacement for the Ollama server. Probes against 0.2.14: `/api/chat` and
`/api/generate` give 404; `/api/tags` and `/api/version` give the web app HTML, not JSON. It serves
OpenAI Chat Completions at `/inference/v1` and Anthropic at `/inference/anthropic` on port 10100, with
other model IDs and a Bearer key from the network. Details and the table: `README.md`.

### Claude Code (owner question: `claude-ol-kat` through Magnitude?)

The alias change is small: the base URL becomes `:10100/inference/anthropic`, the token becomes the network
key, the model ID changes form, the warm-up changes. The real work is on the box: approval for the install,
the fit check (256K-context planning), the chat-template risk (issue #84) and a new quality round.
Details: `README.md`. A local smoke test (Claude Code against Magnitude, one task with a tool call) follows
after the long run.

## Disk (2026-10-29)

Both engines wrote models to the root partition, and root ran full during the downloads.
Necessary changes, done by the owner with sudo:

1. `ollama rm` of `medgemma1.5:4b-it-q8_0`, `medgemma1.5:4b-it-q4_K_M`, `moondream:latest`, `minicpm-v:latest`.
2. Ollama models moved to `/home/ollama-models`. Override
   `/etc/systemd/system/ollama.service.d/override.conf` sets `OLLAMA_MODELS=/home/ollama-models`.
   The old folder `/usr/share/ollama/.ollama/models` is deleted.
3. Magnitude data moved to `/home/magnitude-data`; `/var/lib/magnitude` is a symlink to it.
   The log confirms `Model store resolved root: /home/magnitude-data/models`.
4. Rule from now on: check `df -h / /home` before every download.

## Plan

| Step | What | Est. time | Status |
|---|---|---|---|
| 0 | Project skeleton: AGENTS.md, PLAN.md, GPLv3, `localPipeline.sh`, CI | 30 min | Done |
| 1 | Gate: install Magnitude, check which models load | 30 min | Done (see verdict) |
| 2 | Harness `mvo` (client, workloads A/B/C, runner, report), tests ≥ 95% | 1 h | Done, v0.1.0 |
| 3 | Gemma 4 E2B: Magnitude arms, then Ollama arms (one engine on the GPU at a time) | 1 h | Next |
| 4 | Gemma 4 E4B: same, if Magnitude loads it | 1 h | Open |
| 5 | Qwen3.5 4B forced load on Magnitude: does it load at all? Gate row only | 15 min | Download running |
| 6 | Report + dashboard, README with screenshot, commit | 30 min | Open |
| 7 | Box run for Qwen3.6 35B (only after owner approval) | 2 h | Blocked |
| 8 | Independent review, `review_YYYYMMDD.md`, fixes | 1 h | Open |

Cells per model: `A:4096,A:16384,B:1024,B:8192` with n = 5, and `C:4096` with n = 1 (greedy, 20 tasks).

## Status

| Time | Step | Result |
|---|---|---|
| 2026-10-29 12:40 | Pre-evaluation | Done. |
| 2026-10-29 12:50 | Plan + AGENTS.md | Committed `59ec29f`. |
| 2026-10-29 13:10 | User-space start of Magnitude | Failed: needs the root install. |
| 2026-10-29 13:40 | Harness v0.1.0 | Committed `b07d306`. Pipeline green, 38 tests, 99% coverage. |
| 2026-10-29 13:45 | Ollama smoke, Qwen3.5 4B, 4k | MTP tag 56.8 tok/s, plain 27.7 tok/s decode. Thinking off works. |
| 2026-10-29 14:00 | Owner installed Magnitude (server mode) | Service ready, CUDA seen. |
| 2026-10-29 14:05 | Magnitude catalog check | Qwen3.5 4B refused, Gemma 4 E2B/E4B allowed. |
| 2026-10-29 14:10 | Root partition full (92 MB free) | Stopped all downloads. Owner removed 4 old Ollama models and moved both model stores to `/home` (see "Disk"). |
| 2026-10-29 14:39 | Quick test Gemma 4 E2B | 36 rows, 0 failed. Result in "Verdict so far", point 6. |
| 2026-10-29 14:49 | Long run started (Qwen 2B first) | Stopped at 14:58 after 33 rows (kept) for the new focus. |
| 2026-10-29 15:05 | v0.2.0: workload V, family fix, E4B arms | Chain restarted: Qwen 2B (resumes), then Gemma 4 E4B. |
| 2026-10-29 15:33 | Qwen3.5 2B done | Tie without drafters; Ollama MTP clearly faster. C and V ties. |
| 2026-10-29 16:17 | Gemma 4 E4B done, chain ended | Magnitude 1.81–1.88x on B (clearly faster). C and V ties. 0 failed rows. |
| 2026-10-29 16:20 | v0.3.0: stable warm-up, exclusions; A-4k re-measured | Same 24.6 tok/s: the drafter is off on that prompt. Diagnosis corrected. |
| 2026-10-29 16:22 | Claude Code smoke test via `/inference/anthropic` | Passed: one Write tool call, 2 turns, 25 s. |

## Resume here

- State: laptop round complete. Nothing running. Commits not pushed. Decisions open: see "Open decisions".
- Check: `.venv/bin/mvo report`, `./localPipeline.sh`, `magnitude status`, `ollama ps`, `git log --oneline -5`.
- Re-run a cell: `scripts/run_pair.sh laptop CELLS REPS MAG_ARM MAG_MODEL OLL_ARM OLL_MODEL` (idempotent).
- Full chain: see the usage line in `scripts/run_long.sh`.
