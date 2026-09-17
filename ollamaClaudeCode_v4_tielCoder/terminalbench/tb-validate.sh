#!/usr/bin/env bash
# Offline gate: for every task, prove the SEED fails and the SOLUTION passes, in
# the same --network none verify container the real run will score with. No model
# involved. A task where the seed already "passes" is not broken; a task whose own
# solution fails is not solvable -- both are fixture bugs and must be fixed before
# a model ever sees it (the v4 lesson: validate the fixture first).
set -u
D="$(dirname "$(readlink -f "$0")")"
IMG="v4-tb-sandbox:latest"
fail=0
for task in "$D"/tasks/*/; do
  name=$(basename "$task")
  for variant in seed solution; do
    stage=$(mktemp -d)
    mkdir -p "$stage/work"
    cp -r "$task/seed/." "$stage/work/" 2>/dev/null || true
    [ "$variant" = solution ] && cp -r "$task/solution/." "$stage/work/" 2>/dev/null
    cp "$task/verify.sh" "$stage/verify.sh"
    # test-sha for the tests-untouched guard, if the task uses one
    envs=()
    [ -f "$stage/work/test_roman.c" ] && envs=(-e TB_TEST_SHA="$(sha256sum "$stage/work/test_roman.c" | cut -d' ' -f1)")
    tar czf - -C "$stage" . | \
      docker run --rm -i --network none --user 0 "${envs[@]}" "$IMG" \
        'mkdir -p /v && tar xzf - -C /v && bash /v/verify.sh' >/tmp/tbv.out 2>&1
    rc=$?
    rm -rf "$stage"
    if [ "$variant" = seed ]; then
      if [ $rc -eq 0 ]; then echo "  [BUG] $name seed PASSES verify (not broken)"; fail=1
      else echo "  ok   $name seed fails as expected (rc=$rc)"; fi
    else
      if [ $rc -eq 0 ]; then echo "  ok   $name solution PASSES verify"; else
        echo "  [BUG] $name solution FAILS verify (rc=$rc): $(tail -1 /tmp/tbv.out)"; fail=1; fi
    fi
  done
done
[ $fail -eq 0 ] && echo "ALL TASKS VALID" || echo "FIXTURE BUGS ABOVE"
exit $fail
