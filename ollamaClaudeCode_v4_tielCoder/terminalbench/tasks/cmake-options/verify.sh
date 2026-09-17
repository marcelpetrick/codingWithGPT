#!/usr/bin/env bash
# Deterministic: build 3 configs from clean dirs, check option->output mapping.
set -u
cd "$(dirname "$0")/work" || exit 3
grep -q "option(" CMakeLists.txt 2>/dev/null || { echo "no option()"; exit 1; }
grep -q "target_compile_definitions" CMakeLists.txt 2>/dev/null || { echo "no tcd"; exit 1; }
run() { # args: cmake flags... ; echoes program output
  local d; d=$(mktemp -d)
  cmake -S . -B "$d" "$@" >/dev/null 2>&1 || { echo "__CFG_FAIL__"; return; }
  cmake --build "$d" >/dev/null 2>&1 || { echo "__BUILD_FAIL__"; return; }
  "$d/app" 2>/dev/null || { echo "__RUN_FAIL__"; return; }
}
alloff=$(run)
greet=$(run -DFEATURE_GREET=ON)
math=$(run -DFEATURE_MATH=ON)
stats=$(run -DFEATURE_STATS=ON)
echo "$alloff" | grep -q "^BUILD OK$"           || { echo "no BUILD OK"; exit 1; }
echo "$alloff" | grep -qi "enabled"             && { echo "all-off leaked a feature"; exit 1; }
echo "$greet"  | grep -q "^GREET: enabled$"     || { echo "GREET not enabled"; exit 1; }
echo "$greet"  | grep -q "MATH: enabled"        && { echo "MATH leaked under GREET"; exit 1; }
echo "$math"   | grep -q "^MATH: enabled$"      || { echo "MATH not enabled"; exit 1; }
echo "$stats"  | grep -q "^STATS: enabled$"     || { echo "STATS not enabled"; exit 1; }
echo "SOLVED"; exit 0
