# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Placebo check of the direct-evidence rule: real comment lines against lines shifted by k.

Usage: uv run python scripts/placebo_check.py <db>. Prints aggregate rates only.
"""

import sqlite3
import sys

from mrreview.evaluate import LINE_RADIUS, old_side_changes

FILES_SQL = """WITH lastv AS (SELECT project_id, mr_iid, max(version_id) v FROM mr_versions
 WHERE diffs_complete=1 GROUP BY 1, 2)
 SELECT l.project_id, l.mr_iid, count(*) FROM lastv l JOIN version_diffs d
 ON d.project_id=l.project_id AND d.mr_iid=l.mr_iid AND d.version_id=l.v GROUP BY 1, 2"""
ROWS_SQL = """SELECT t.project_id, t.mr_iid, t.new_line, c.file_diff FROM code_changes c
 JOIN threads t ON t.id=c.thread_id WHERE c.status != 'unavailable' AND c.file_changed=1
 AND t.new_line IS NOT NULL AND t.substantive=1"""


def bucket(n: int | None) -> str:
    if n is None:
        return "unknown"
    return "20+" if n >= 20 else "10-19" if n >= 10 else "5-9" if n >= 5 else "1-4"


def main(db: str) -> None:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    files = {(p, i): n for p, i, n in conn.execute(FILES_SQL)}
    rows = conn.execute(ROWS_SQL).fetchall()
    shifts = (10, 25, 50, 100)
    total = {k: [0, 0] for k in shifts}
    real = 0
    by_size: dict[str, list[int]] = {}
    for pid, iid, line, diff in rows:
        changed = old_side_changes(diff)

        def near(x: int, changed: set[int] = changed) -> bool:
            return any(abs(m - x) <= LINE_RADIUS for m in changed)

        real += near(line)
        size = by_size.setdefault(bucket(files.get((pid, iid))), [0, 0, 0, 0])
        size[0] += 1
        size[1] += near(line)
        for k in shifts:
            for x in (line - k, line + k):
                if x >= 1:
                    total[k][0] += near(x)
                    total[k][1] += 1
                    if k == 50:
                        size[2] += near(x)
                        size[3] += 1
    print(f"threads with a changed file: {len(rows)}, real direct: {100 * real / len(rows):.1f}%")
    for k, (hit, n) in total.items():
        print(f"placebo +-{k} lines: {100 * hit / n:.1f}%")
    for name in sorted(by_size):
        n, hit, phit, pn = by_size[name]
        print(
            f"MR files {name}: n={n} real {100 * hit / n:.1f}% placebo50 {100 * phit / max(pn, 1):.1f}%"
        )


if __name__ == "__main__":
    main(sys.argv[1])
