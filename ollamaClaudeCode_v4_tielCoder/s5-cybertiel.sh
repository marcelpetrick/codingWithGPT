#!/usr/bin/env bash
# s5-cybertiel.sh — Stage C of plan.md: benchmark the abliterated CyberTiel,
# same battery as Tiel's S1, plus SANDBOXED sessions and a benign refusal probe.
#
# Prereqs: the Q5 pull has finished and the pp-0 variant is baked (see below),
# and the sandbox image is built (docker build -t v4-cc-sandbox sandbox/).
set -uo pipefail
D="$(dirname "$(readlink -f "$0")")"
RAW="hf.co/peculiar-ragdoll/Cyber-Tiel-Coder-35B-A3B-GGUF:UD-Q5_K_XL"
M="cyber-tiel:35b-q5-ctx256k-agentic"

# Bake the deployable variant: 262k window, presence_penalty 0 (the card lists no
# penalty; temp 0.6/top_p .95/top_k 20 are its agentic-coding sampling defaults).
curl -s http://192.168.100.67:11434/api/create -d "{\"model\":\"$M\",\"from\":\"$RAW\",\"parameters\":{\"num_ctx\":262144,\"presence_penalty\":0,\"temperature\":0.6,\"top_p\":0.95,\"top_k\":20},\"stream\":false}"; echo

# C2 — server battery, identical to Tiel's S1.
./idle.sh --mine "$M"
./kv-probe.sh --model "$M" --ctxs "65536 131072 262144" | tee results/kv-ladder-cybertiel.txt
GATE_RUNS=3 NEEDLE_DEPTHS="2700 10700 40000 80000 110000 125000 135000" ./head2head.sh "$M"

# C4 — benign over-refusal probe: CyberTiel vs the censored Tiel, same prompts.
./idle.sh --mine "$M"
python3 ./refusal-probe.py "$M" "Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest"

# C3 — sandboxed sessions, easy + hard, n=3.
./idle.sh --mine "$M"
./cc-session-sandboxed.sh --fixture easy --runs 3 "$M"
./cc-session-sandboxed.sh --fixture hard --runs 3 "$M"
./idle.sh --mine "$M"
echo S5-DONE
