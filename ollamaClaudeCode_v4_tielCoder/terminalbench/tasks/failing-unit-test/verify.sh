#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/work" || exit 3
# tests must be untouched
if [ -n "${TB_TEST_SHA:-}" ]; then
  now=$(sha256sum test_roman.c | cut -d' ' -f1)
  [ "$now" = "$TB_TEST_SHA" ] || { echo "test_roman.c was modified"; exit 2; }
fi
make clean >/dev/null 2>&1
make test >/dev/null 2>&1 || { echo "build failed"; exit 1; }
out=$(./test 2>/dev/null); rc=$?
[ $rc -eq 0 ] || { echo "tests failed: $out"; exit 1; }
echo "$out" | grep -q "ALL PASS" || { echo "no ALL PASS: $out"; exit 1; }
echo "SOLVED"; exit 0
