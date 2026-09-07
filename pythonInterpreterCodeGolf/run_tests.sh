#!/usr/bin/env bash
# Build every version, diff its output against CPython, and report the byte count.
# Usage: ./run_tests.sh [source...]     (default: all of src/pygolf_v*.c)
#
# v1..v9 implement the full documented subset and are checked against every
# program in tests/ plus program.py. v10 and v11 are the FizzBuzz-only
# minimum and are checked against program.py alone - see README.md.
set -u

cd "$(dirname "$0")"
mkdir -p build
full=(program.py tests/*.py)
srcs=("$@")
[ ${#srcs[@]} -eq 0 ] && srcs=($(ls src/pygolf_v*.c | sort -V))
fail=0

printf '%-14s %7s  %s\n' VERSION BYTES RESULT
for src in "${srcs[@]}"; do
    name=$(basename "$src" .c)
    bytes=$(wc -c < "$src")
    case "$name" in
        pygolf_v10|pygolf_v11) cases=(program.py) ;;
        *)                     cases=("${full[@]}") ;;
    esac
    if ! gcc -std=gnu89 -w -O1 -o "build/$name" "$src" 2>"build/$name.log"; then
        printf '%-14s %7d  BUILD FAILED (see build/%s.log)\n' "$name" "$bytes" "$name"
        fail=1
        continue
    fi
    bad=()
    for case in "${cases[@]}"; do
        diff -q <("build/$name" < "$case" 2>&1) <(python3 "$case") >/dev/null \
            || bad+=("$(basename "$case")")
    done
    if [ ${#bad[@]} -eq 0 ]; then
        printf '%-14s %7d  ok (%d/%d match CPython)\n' \
               "$name" "$bytes" "${#cases[@]}" "${#cases[@]}"
    else
        printf '%-14s %7d  FAIL: %s\n' "$name" "$bytes" "${bad[*]}"
        fail=1
    fi
done
exit $fail
