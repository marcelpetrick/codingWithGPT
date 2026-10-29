# PLAN: Magnitude versus Ollama

Living document. Started 2026-10-29.

## Verdict so far

Not measured yet. Pre-evaluation results (web, 2026-10-29):

1. Qwen3.6 35B-A3B cannot run with Magnitude on this laptop. The Q4 download is 24.2 GB.
   The GPU has 8 GB. Magnitude has no CPU offload for MoE experts (issue #194, open).
2. The only Qwen model that both engines can run here is Qwen3.5 4B at Q4.
   Even this can fail: an 8 GB RTX 3070 user reports a refusal, because Magnitude plans
   memory for the full 262k context (issue #153, open).
3. The vendor claim ("2x faster than Ollama") is from one workload only. Treat it as a claim.
   See "Angles" below.

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
| `magnitude-default` | Magnitude, catalog default | DFlash (if it runs) |
| `ollama-default` | Ollama 0.40.4, tag default | whatever the tag ships |
| `ollama-nodraft` | Ollama, drafter off (if the tag has one) | none |
| `magnitude-nodraft` | Magnitude, drafter off (if a switch exists) | none |

The `nodraft` arms separate "kernel tuning" from "speculative decoding".

## Sites

| Site | GPU | Models | Status |
|---|---|---|---|
| Laptop (this machine) | RTX A2000 8 GB Laptop, sm_86, driver 610.57.04; i9-12900H; 31 GB RAM | Qwen3.5 4B Q4 | Go |
| Box `192.168.100.67` | ~35.5 GB VRAM, Ollama 0.40.11 | Qwen3.6 35B-A3B Q4 (`qwen3.6:35b-a3b-q4_K_M-agentic-t06` is present) | Blocked: needs owner approval to install Magnitude (shared box) |

## Plan

| Step | What | Est. time |
|---|---|---|
| 0 | Project skeleton: AGENTS.md, PLAN.md, GPLv3, `localPipeline.sh`, CI | 30 min |
| 1 | Gate: unpack Magnitude in user space (no sudo), start it, list models, try to load Qwen3.5 4B Q4 | 30 min |
| 2 | Engine-agnostic bench client `scripts/bench.py` (OpenAI streaming, TTFT, prefill, decode), with tests | 1 h |
| 3 | Workload files A, B, C, quality checker | 1 h |
| 4 | Run Ollama arms, then Magnitude arms (one engine at a time) | 1–2 h |
| 5 | Report generator: `report.md` + sortable HTML dashboard from `results/*.jsonl` | 1 h |
| 6 | Box run for Qwen3.6 35B (only after approval) | 2 h |
| 7 | Independent review, `review_YYYYMMDD.md`, fixes | 1 h |

## Status

| Time | Step | Result |
|---|---|---|
| 2026-10-29 12:40 | Pre-evaluation | Done. Findings in "Verdict so far". |
| 2026-10-29 12:50 | Plan + AGENTS.md | Committed. |

## Resume here

- State: plan written. No measurement yet.
- Next: step 0 (skeleton), then step 1 (gate).
- Check commands: `ollama ps`, `nvidia-smi`, `./localPipeline.sh`.
