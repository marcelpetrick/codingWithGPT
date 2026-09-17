#!/usr/bin/env bash
# s2-field.sh — stage S2 of plan.md: the v3 field, re-measured on Ollama 0.33.3.
#
# Throughput, residency, the T1-T7 battery once, vision where the model has it,
# and ONE needle rung per model: the deepest depth that model verified in v3.
# Retrieval depth proved version-stable across 0.32.9 -> 0.32.15, so this is a
# spot check that it survived 0.33.3, not a re-derivation of the ladder.
# Depths are in words, as needle-v2.sh takes them (v3 measurements.md §8, §16, §31).
set -uo pipefail
D="$(dirname "$(readlink -f "$0")")"
run() {
  NEEDLE_DEPTHS="$2" GATE_RUNS=1 "$D/head2head.sh" "$1"
  # v4 addition: cold vs warm prefill. 0.33.3 caches the prompt prefix and
  # 0.32.15 did not (review.md R2), so this is measured per model rather than
  # inherited from v3's "you pay prefill every turn".
  "$D/idle.sh" --mine "$1"
  python3 "$D/cache-probe.py" "$1"
  # Which overflow regime is this model in? v1-v3 found that exceeding num_ctx
  # silently keeps half the window and stops tool calling. On 0.33.3 that is
  # STILL live for ornith and north-mini, while Tiel returns HTTP 400 instead --
  # so it is a property of the build, not the runtime, and worth knowing per
  # model: an error is recoverable, a silently halved context is not.
  "$D/idle.sh" --mine "$1"
  python3 "$D/overflow-probe.py" "$1"
  "$D/idle.sh" --mine "$1"
}

run "qwen3.6:35b-a3b-q4_K_M-agentic"                "80000"    # control first: 146,957 tok
run "north-mini-code-1.0:q4_K_M-ctx256k-agentic"    "140000"   # 201,737 tok
run "gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic"      "80000"    # 143,324 tok
run "ornith:35b-ctx256k-agentic"                    "135000"   # 254,061 tok
run "nemotron-3.5-lightning:30b-ctx256k-agentic"    "80000"    # 161,516 tok
run "nemotron-cascade-2:30b-ctx256k-agentic"        "80000"    # 161,526 tok
run "qwen3.8:27b-q4_K_M-ctx128k-agentic"            "65000"    # 119,015 tok
# The two Tiel tags get the same cache measurement, for the same table.
"$D/idle.sh"
python3 "$D/cache-probe.py" "Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest"
python3 "$D/overflow-probe.py" "tiel-coder:35b-q5-ctx256k-agentic"
"$D/idle.sh" --mine "Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest"
echo S2-DONE
