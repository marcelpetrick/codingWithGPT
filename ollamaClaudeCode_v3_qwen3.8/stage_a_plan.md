# Stage A — the Qwen3.8 run

Written **2026-08-27**, before any Qwen3.8 measurement. Nothing here is a result;
results land in [`measurements.md`](measurements.md) §12–16 and the verdict in
[`README.md`](README.md).

[`plan.md`](plan.md) §1 parked this stage behind one blocker. The blocker is gone.

---

## 1. The blocker cleared

```console
$ curl -s http://192.168.100.67:11434/api/version
{"version":"0.32.15"}
$ curl -s http://192.168.100.37:11434/api/version
{"version":"0.32.15"}
```

Both boxes moved from **0.32.9 to 0.32.15** — exactly the target `market_research.md` §1
recommended, not the 0.33.0 pre-release. The registry gate is open: every Qwen3.8 manifest
carries `"requires":"0.32.12"`, and 0.32.15 clears it. Verified by resolving the manifests
before pulling a byte, rather than by watching a pull fail.

## 2. What the registry actually ships

Resolved from `registry.ollama.ai` on 2026-08-27, before the pull:

| tag | weights blob | total | params layer |
|---|---|---|---|
| `qwen3.8:27b-q4_K_M` | `f5f1dd8920d4` 15.656 GiB | 16.52 GiB | `448d2943…` |
| `qwen3.8:27b-mtp-q4_K_M` | `f5f1dd8920d4` **same** | 16.52 GiB | `906ee87b…` |
| `qwen3.8:27b` *(default)* | `f5f1dd8920d4` **same** | 16.52 GiB | `906ee87b…` **= mtp** |
| `qwen3.8:27b-q8_0` | `2bb227142898` 27.052 GiB | 27.92 GiB | `448d2943…` |

All four carry the same 0.867 GiB `projector` layer — the vision encoder — and the same
config: `model_type 27.3B`, `model_family qwen35`, `renderer qwen3.8`, `parser qwen3.5`.

Three things follow, and two of them change what this stage costs:

- **A2 is nearly free.** MTP is not different weights. It is the same 15.656 GiB blob plus a
  different params layer, so the second tag downloads a few hundred bytes. Re-testing v2's
  MTP finding costs bench time only.
- **`qwen3.8:27b` — the tag a person types — is the MTP build.** Its params digest is
  byte-identical to `27b-mtp-q4_K_M`'s. Anyone pulling the obvious name gets speculative
  decoding switched on without asking for it, which matters because v2 measured that as a
  *net loss* on this box.
- **The shipped params are already clean of v2's expensive footgun:**
  ```json
  27b-q4_K_M      {"min_p":0,"presence_penalty":0,"repeat_penalty":1,"temperature":1,"top_k":20,"top_p":0.95}
  27b-mtp-q4_K_M  {"draft_num_predict":4, …same…}
  ```
  `presence_penalty` is 0, so v2's 31–35% throughput tax is fixed upstream. **Neither ships
  `num_ctx`**, so both inherit the 16,384 default and the baking step stays mandatory.

## 3. Does it fit in 40 GB?

The budget is the measured one, not the datasheet: **≈35.5 GB usable**, established in v2
(`muse_ollama.md` §11.4) when a dense q8_0 asked for 38.33 GB and only 35.56 GB stayed
resident. No Ollama API exposes VRAM, so 40.4 GB was always human-supplied.

Weights are the floor, not the answer — a dense 27B's KV cache is the variable that decides
the window:

| rung | weights + projector | left for KV | prediction |
|---|---|---|---|
| **A1 q4_K_M** | ≈17.7 GB | ≈17.8 GB | **fits comfortably.** The only question is how much window that buys |
| **A2 mtp-q4_K_M** | ≈17.7 GB | ≈17.8 GB | identical footprint; MTP costs throughput, not memory |
| **A3 q8_0** | ≈30.0 GB | ≈5.5 GB | **fits, barely, with a small window.** v2's dense q8 sibling topped out at `num_ctx 81920` |

The nearest measured reference point is the dense stand-in this project already ran:
`qwen3.6:27b-q4_K_M` held **131,072 tokens in 30.17 GB** and `q8_0` held **81,920 in
34.03 GB**. Qwen3.8 is the same family string (`qwen35`) and the same 27B dense class, so
those are the numbers to expect — and step 3 below measures rather than assumes it.

**Prediction to be falsified:** A1 reaches 131,072 at 100% GPU and does *not* reach 262,144;
A3 lands near 81,920. If A1 clears 262,144 the dense KV is cheaper than the sibling's and
that is the finding.

## 4. Protocol — unchanged from `plan.md` §3

Same harness, same order, `./idle.sh` asserted between every stage. Steps 1–8 per rung:
bake `-agentic` → residency at 100% GPU → `kv-probe` ladder → `tokrate` at 0/2k/20k words →
tool gates T1–T7 → `needle-v2` at `--num-predict 2048` → `cliff-probe` → vision.

Two Stage-A-specific notes:

- **`kv-probe.sh` needs `--port 11434`.** Its default is `127.0.0.1:11435`; `--host` alone
  sends everything to a dead port and the failure reads as a JSON decode error, not a
  connection error. This cost time once already (`README.md`).
- **A3 runs only if A1 earns it** (`plan.md` §2). If A1 is too slow to recommend, a slower,
  more expensive rung of the same model does not change the verdict.

## 5. The version problem, and the control

This is the one thing the upgrade broke, and it is not optional.

**Every number in this repository was measured on Ollama 0.32.9. Every Qwen3.8 number will
be measured on 0.32.15.** `plan.md` §2 C1 called this out in advance: comparing across
runtime versions is comparing two things at once.

So the control is re-measured **first**, on 0.32.15, before any Qwen3.8 number is taken:

| | |
|---|---|
| model | `qwen3.6:35b-a3b-q4_K_M-agentic` @ 262144 |
| 0.32.9 baseline | **130.0 tok/s** generation, 3,911 tok/s prefill @35k |
| decision rule | within ±5% → the v3 tables stand and Qwen3.8 compares against them directly. Outside ±5% → **every** cross-version comparison in this repo is annotated, and the version delta is reported as a finding in its own right |

`north-mini-code-1.0` is re-measured as a second version-delta point, because one model
moving could be that model and two models moving is the runtime.

**`idle.sh` treats `qwen3.6:*` as foreign on purpose** — it cannot tell a colleague's
`claude-ol2` session from our control run. So the control needs `--force`, and `--force` is
used only after `/api/ps` is confirmed empty by hand.

## 6. What would make this stage report "no"

Stated before the numbers exist, so it cannot be rationalised afterwards:

- **A1 lands under ~40 tok/s.** Then Qwen3.8's benchmark wins (Terminal-Bench 63.4 → 73.0,
  SWE-bench Pro 53.5 → 61.7) do not transfer into an agentic loop on this box, and the
  honest verdict is "smarter, and you will not want to use it". `plan.md` §6 predicted this
  as the likely outcome; the dense field measured here runs 19–31 tok/s.
- **A1 fails a tool gate.** Laguna was the fastest challenger in the field and is not
  recommended for exactly this reason. Tool-call reliability is pass/fail, not a gradient.
- **The window does not reach 131,072 at 100% GPU.** A dense 27B that cannot hold a Claude
  Code session's context is not a Claude Code model regardless of its speed.

Any of those and the incumbent holds. That is a real possible result of this stage.
