#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/work" || exit 3
gcc -O0 -g -o prices prices.c 2>/dev/null || { echo "does not compile"; exit 1; }
out=$(./prices 2>/dev/null); rc=$?
[ $rc -eq 0 ] || { echo "crashed/nonzero rc=$rc"; exit 1; }
echo "$out" | grep -q "pear costs 45 cents" || { echo "wrong output: $out"; exit 1; }
# guard: price data untouched (still 45 for pear)
grep -q '"pear", 45' prices.c || { echo "price data changed"; exit 1; }
echo "SOLVED"; exit 0
