# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare LLM classifications of the synthetic fixture with its ground truth (REQ-LLM-4).

Usage: uv run python scripts/truth_check.py <db_path> [seed]
Prints the agreement of the first finding's text outcome per scenario. Synthetic data only.
"""

import collections
import json
import sqlite3
import sys

from mrreview.demo.fixture import build_fixture

EXPECT: dict[str, set[str]] = {
    "defect_fixed": {"implemented_claimed"},
    "defect_fixed_de": {"implemented_claimed"},
    "defect_fixed_fr": {"implemented_claimed"},
    "security_fixed": {"implemented_claimed"},
    "design_rebutted": {"justified_no_change"},
    "test_partial": {"partial_claimed", "implemented_claimed"},
    "nit_declined": {"optional_declined"},
    "deferred": {"deferred"},
    "promise_no_fix": {"promised"},
    "unanswered": {"open"},
    "silent_fix": {"open"},
    "alternative": {"alternative_claimed"},
    "clarified": {"justified_no_change"},
    "dismissive": {"declined_unjustified"},
    "long_discussion": {"implemented_claimed"},
    "plus_one_docs": {"implemented_claimed"},
    "html_injection": {"implemented_claimed"},
    "open_recent": {"promised"},
}


def main() -> int:
    fx = build_fixture(int(sys.argv[2]) if len(sys.argv) > 2 else 7)
    conn = sqlite3.connect(sys.argv[1])
    by: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    ok = n = 0
    per_thread: collections.Counter[int] = collections.Counter()
    rows = conn.execute(
        "SELECT thread_id, result_json, prompt_version FROM classifications WHERE status='ok'"
    ).fetchall()
    for tid, result, _pv in rows:
        key = fx.truth[tid]
        findings = json.loads(result)
        per_thread[len(findings)] += 1
        outcome = findings[0]["text_outcome"] if findings else "(none)"
        by[key][outcome] += 1
        if key in EXPECT:
            n += 1
            ok += outcome in EXPECT[key]
    versions = sorted({r[2] for r in rows})
    print(f"prompt {versions}: {ok}/{n} = {ok / n:.3f} agreement with the scenario truth")
    print("findings per thread:", dict(sorted(per_thread.items())))
    for key, counts in sorted(by.items()):
        mark = "" if key not in EXPECT or set(counts) <= EXPECT[key] else "  <-- differs"
        print(f"  {key}: {dict(counts)}{mark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
