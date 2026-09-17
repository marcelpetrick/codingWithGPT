#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/work" || exit 3
make clean >/dev/null 2>&1
make >/dev/null 2>&1 || { echo "make failed"; exit 1; }
out=$(./app 2>/dev/null); rc=$?
[ $rc -eq 0 ] || { echo "run rc=$rc"; exit 1; }
echo "$out" | grep -q "^vowels=5 len=18$" || { echo "wrong output: $out"; exit 1; }
echo "SOLVED"; exit 0
