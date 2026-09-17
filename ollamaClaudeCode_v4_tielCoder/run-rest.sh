#!/usr/bin/env bash
# run-rest.sh — everything still owed after S1 and the review, in one chain so the
# box is never idle between stages. Each stage is guarded with `|| true`: a model
# that fails must not cancel the seven after it.
#
#   S2  the v3 field, re-measured on 0.33.3 (+ cold/warm prefill per model)
#   S3  Claude Code sessions, both fixtures, n=3, round-robin over the field
#   S3p harness parity: the SAME Tiel tag through the host and the sandbox
#       harness, so CyberTiel-vs-Tiel is not confounded by the container
#       (review.md R4)
#   S5  CyberTiel: full battery, benign refusal probe, sandboxed sessions
#
# Usage: ./run-rest.sh            (logs to results/rest.log)
set -uo pipefail
D="$(dirname "$(readlink -f "$0")")"
cd "$D"
T1="Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest"

banner() { printf '\n\033[1m==================== %s ====================\033[0m\n' "$1"; date -Is; }

banner "S2 — the field on Ollama 0.33.3"
./s2-field.sh || true

banner "S3 — sessions, both fixtures, n=3, round-robin"
RUNS=3 ./s3-sessions.sh || true

banner "S3p — harness parity: Tiel through host and sandbox"
# Three sandboxed runs of the tag that already has three host runs. The delta
# between these two rows is the container, and it is what makes the later
# CyberTiel(sandbox) vs Tiel(sandbox) comparison honest.
./idle.sh --mine "$T1" || true
./cc-session-sandboxed.sh --fixture easy --runs 3 "$T1" || true
./cc-session-sandboxed.sh --fixture hard --runs 3 "$T1" || true
./idle.sh --mine "$T1" || true

banner "S5 — CyberTiel (abliterated): battery, refusal probe, sandboxed sessions"
./s5-cybertiel.sh || true

banner "ALL DONE"
echo REST-DONE
