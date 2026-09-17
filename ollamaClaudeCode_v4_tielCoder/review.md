# v4 self-review — 2026-09-17, after stage S1

Written after S1 finished and before S2/S3/S5 ran, because a harness flaw found late is a
re-run of everything. Twelve findings, each with what was done about it. Four changed results
rather than tidiness: **R1/R2** (the runtime caches prompts now), **R4** (the sandbox is a
different environment), **R6** (a single gate failure is not a gate failure) and **R11** (three
"measurements" that measured nothing at all).

The two worth reading in full are R1/R2 and R11. R11 in particular is the argument for doing
this at all: I had already fixed that exact footgun in one script, carried the unfixed version
of it in another, and published three rows from it in a notification before checking them.

| # | finding | severity | mitigation |
|---|---|---|---|
| R1 | T7 printed "3/3 at **4** tokens" and I nearly published it as a context claim | **high** | the harness read only `usage.input_tokens`; 0.33.3 splits the prompt into `input_tokens` + `cache_read_input_tokens`. Both are now summed and reported |
| R2 | **0.33.3 does incremental prefix caching; 0.32.15 did not** | **high** | new `cache-probe.py`, run per model in S2. v3's "prefill beats generation" rule is re-derived rather than inherited |
| R3 | the easy fixture existed twice: a heredoc inside `cc-session.sh` and `fixtures/easy/` | medium | one source of truth: both harnesses copy `fixtures/easy/` |
| R4 | host sessions run on Python 3.14/pytest 9.1, sandbox on 3.11/pytest 7.2 — so CyberTiel-vs-Tiel would confound model with environment | **high** | the fixture is re-validated inside the image, and Tiel runs in **both** harnesses so the harness delta is measured, not assumed |
| R5 | Tiel's needle ladder passed every rung, so "deepest verified" was a floor, not a ceiling | medium | deeper rungs added until the cliff is located |
| R6 | the pp-0 variant FAILed T5 once; the shipped tag passed it 3/3 | medium | `gate-rerun.py`, n=8 on both tags, before either number is believed |
| R7 | `tokrate` caps `num_predict` at 256 but models stop earlier (182–254), so gen tok/s is measured over a short window | low | noted with every figure; unchanged for comparability with v1–v3 |
| R8 | no reproducibility block (digests, versions) as the brief requires | low | `results/provenance.txt`, generated |
| R9 | `vision-bench` claims `think:false` is honoured but never checked it | low | the TSV carries a `thinking_chars` column; asserted per model |
| R10 | S1 results were uncommitted while later stages could overwrite them | low | committed per stage |
| R11 | **`needle-v2.sh` defaults to `127.0.0.1`**, so the deep rungs I ran to find Tiel's cliff silently measured *nothing*: empty responses scored `PARSE_FAIL` and the baked-window probe fell back to 32768 | **high** | default moved to `.67`, and an unreachable host now exits 2 with a message instead of producing rows. This is the same footgun class v3 documented for `kv-probe`'s dead port — I fixed it there and missed it here, which is exactly why the review was worth doing |
| R12 | `cache-probe`'s "cold" row included the model load after an idle server (1,281 tok/s against a true 3,659) | medium | the probe warms the weights with a trivial request first; the load cost is `tokrate`'s `load_s`, reported separately |

## R1/R2 in full — the runtime changed the rules again

v3's headline was "the runtime version is a variable". It still is, and 0.33.3 moved something
bigger than throughput. Measured directly (`cache-probe.py`, Tiel Q5, 30k-token prompts):

| request | prefilled | served from cache | wall | implied prefill |
|---|---|---|---|---|
| cold, unique prompt | 30,042 | 178 | 7.85 s | 3,848 tok/s |
| **the same prompt again** | **4** | 30,216 | **0.64 s** | 47,114 tok/s |
| **same prefix, new tail** | **517** | 29,708 | 0.94 s | 32,149 tok/s |
| a different unique prompt | 30,045 | 178 | 8.31 s | 3,637 tok/s |

Every v3 gate response and every v3 session reports `cache_read = 0`; on 0.33.3 the third row
is the one that matters, because that is exactly the shape of an agent turn — a stable prefix
with a tool result appended. **The agent no longer re-reads its context every turn.**

Consequences, stated before the field is measured so they cannot be fitted afterwards:

1. **v3's ranking rule "prefill beats generation for this workload" is suspended**, not
   inherited. Cold prefill still sets the cost of the *first* turn of a session; generation and
   turn count set the rest.
2. A session wall clock on 0.33.3 is not comparable with one on 0.32.15, on top of the
   throughput differences v3 already documented.
3. Both numbers get reported per model: **cold** prefill (`tokrate`, unique prompts) and
   **warm/incremental** prefill (`cache-probe`).

## R4 in full — the sandbox is a different computer

CyberTiel must run sandboxed (it is abliterated), Tiel ran on the host, and the two
environments are not the same: Python 3.14 vs 3.11, pytest 9.1 vs 7.2, different CPU limits
(`--memory 2g`, `--pids-limit 512`). Comparing a sandboxed CyberTiel session against a host
Tiel session would confound the model with its harness.

Mitigation, in two parts:
1. the ledger fixture is re-validated **inside the image** — the buggy original must fail 9/9
   visible and pass only the 3 regression guards, the reference solution must pass 18/18 —
   so pytest 7 vs 9 is not silently changing what "PASS" means;
2. **Tiel runs in both harnesses** (host and sandbox). Any difference between those two rows
   is the harness, and the CyberTiel-vs-Tiel comparison is drawn **sandbox-to-sandbox**.
