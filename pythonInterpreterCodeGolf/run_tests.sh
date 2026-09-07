#!/usr/bin/env bash
# Build every version, check its output against CPython, and report the byte count.
# Usage: ./run_tests.sh [version...]     (default: all of src/pygolf_v*.c)
set -u

cd "$(dirname "$0")"
mkdir -p build
cases=(program.py tests/*.py)
srcs=("$@")
[ ${#srcs[@]} -eq 0 ] && srcs=(src/pygolf_v*.c)
fail=0

printf '%-18s %7s  %s\n' VERSION BYTES RESULT
for src in "${srcs[@]}"; do
    name=$(basename "$src" .c)
    bytes=$(wc -c < "$src")
    if ! gcc -std=gnu89 -w -O1 -o "build/$name" "$src" 2>build/$name.log; then
        printf '%-18s %7d  BUILD FAILED (see build/%s.log)\n' "$name" "$bytes" "$name"
        fail=1
        continue
    fi
    bad=()
    for case in "${cases[@]}"; do
        if ! diff -q <("build/$name" < "$case" 2>&1) <(python3 "$case") >/dev/null; then
            bad+=("$(basename "$case")")
        fi
    done
    if [ ${#bad[@]} -eq 0 ]; then
        printf '%-18s %7d  ok (%d/%d programs match CPython)\n' \
               "$name" "$bytes" "${#cases[@]}" "${#cases[@]}"
    else
        printf '%-18s %7d  FAIL: %s\n' "$name" "$bytes" "${bad[*]}"
        fail=1
    fi
done
exit $fail
