# PLAN: Magnitude versus Ollama

Living document. Started 2026-10-29.

## Verdict so far

No speed result yet. Gate results on this laptop (2026-10-29):

1. **Magnitude installs and runs here.** Version 0.2.14, CUDA on the RTX A2000, service "Ready".
2. **Qwen3.6 35B-A3B: blocked.** The Q4 is 24.2 GB, the GPU has 8 GB. Magnitude cannot put MoE
   experts in system RAM (issue #194, open). Ollama can, but that is a CPU-offload test, not a match.
3. **Qwen3.5 4B: Magnitude refuses it.** It plans memory for the full 262144 context. The catalog Q4
   needs 9.9 GB (392 MB short). Every Hugging Face quant is "too large", even the 1.52 GB one.
   Ollama runs the same model at 16k context in 1.4 GB (MTP tag) or 3.7 GB (plain tag), 100% GPU.
   This matches issue #153 (8 GB RTX 3070, same refusal). A forced download tests if it loads anyway.
4. **The overlap is Gemma 4 E2B and E4B (QAT Q4).** Magnitude allows them here, Ollama has the same
   QAT tags, and the vendor published numbers for both (decode 1.51x and 1.65x on DGX Spark).
5. The vendor claim ("2x faster than Ollama") is from one workload only. Treat it as a claim.
6. **Quick test, Gemma 4 E2B (site `laptop-quick`, n = 3, does not pool):** Magnitude (MTP drafter)
   vs Ollama (no drafter tag exists). Repeat-a-passage decode 269 vs 50 tok/s (5.4x). New-code decode
   58 [50–96] vs 51 [51–51] tok/s (1.15x, a **tie** under the rule). Prefill at 3k tokens 6608 vs
   1560 tok/s (4.2x). The decode gain is the drafter on repeated text. The prefill gain is real.

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

## Resume here

- State: Magnitude service runs. Downloads: `gemma-4-e2b-it-qat:gguf:q4` and the forced Qwen3.5 4B
  (Magnitude); `gemma4:e2b-it-qat`, `gemma4:e4b-it-qat` (Ollama, log in `~/magnitude_eval/`).
- Check: `magnitude models status`, `ollama list`, `ollama ps`, `nvidia-smi`, `./localPipeline.sh`.
- Next: add the Gemma arms to `arms.json`, put the network key in `MVO_MAGNITUDE_API_KEY`
  (environment only), then run step 3.
