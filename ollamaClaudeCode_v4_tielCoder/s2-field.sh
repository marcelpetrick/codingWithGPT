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
run() { NEEDLE_DEPTHS="$2" GATE_RUNS=1 "$D/head2head.sh" "$1"; }

run "qwen3.6:35b-a3b-q4_K_M-agentic"                "80000"    # control first: 146,957 tok
run "north-mini-code-1.0:q4_K_M-ctx256k-agentic"    "140000"   # 201,737 tok
run "gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic"      "80000"    # 143,324 tok
run "ornith:35b-ctx256k-agentic"                    "135000"   # 254,061 tok
run "nemotron-3.5-lightning:30b-ctx256k-agentic"    "80000"    # 161,516 tok
run "nemotron-cascade-2:30b-ctx256k-agentic"        "80000"    # 161,526 tok
run "qwen3.8:27b-q4_K_M-ctx128k-agentic"            "65000"    # 119,015 tok
echo S2-DONE
