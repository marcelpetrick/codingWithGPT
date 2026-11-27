# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write the final project report as one HTML file: aggregates only, no person or project names.

Usage: uv run python scripts/final_report.py <db> <annotation_summary.json> <out.html>
"""

import html
import json
import sqlite3
import sys
from collections import Counter
from datetime import UTC, datetime

from mrreview.evaluate import LINE_RADIUS, old_side_changes

OUTCOME_TIPS = {
    "implemented": "A change is stated in the text, or a promise has a direct code change.",
    "alternative_implemented": "A different fix than requested is stated.",
    "partially_implemented": "Part of the request is stated as done.",
    "justified_no_change": "A reasoned answer shows no change is needed.",
    "optional_declined": "An optional suggestion is declined.",
    "deferred": "Moved to later work.",
    "declined_unjustified": "Rejected with no reason.",
    "open": "No decision, or only a promise without code evidence.",
    "unknown": "The model abstained.",
}


def esc(x: object) -> str:
    return html.escape(str(x))


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}%" if b else "n/a"


def bars(rows: list[tuple[str, int, str]], total: int) -> str:
    peak = max((n for _, n, _ in rows), default=1) or 1
    out = []
    for name, n, tip in rows:
        w = 100 * n / peak
        out.append(
            f'<div class="row" title="{esc(tip)}"><span class="lbl">{esc(name)}</span>'
            f'<span class="track"><span class="bar" style="width:{w:.1f}%"></span></span>'
            f'<span class="val">{n:,} <small>({pct(n, total)})</small></span></div>'
        )
    return '<div class="bars">' + "".join(out) + "</div>"


def table(head: list[str], rows: list[list[object]], tips: list[str] | None = None) -> str:
    th = "".join(
        f'<th title="{esc(tips[i]) if tips else ""}">{esc(h)}</th>' for i, h in enumerate(head)
    )
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def placebo(conn: sqlite3.Connection) -> list[list[object]]:
    rows = conn.execute(
        """SELECT t.new_line, c.file_diff FROM code_changes c JOIN threads t ON t.id=c.thread_id
        WHERE c.status != 'unavailable' AND c.file_changed=1 AND t.new_line IS NOT NULL
        AND t.substantive=1"""
    ).fetchall()
    hits = Counter()
    tries = Counter()
    for line, diff in rows:
        changed = old_side_changes(diff)
        for k in (0, 10, 25, 50, 100):
            x = line - k  # upward only: the line exists in the file for sure
            if x >= 1:
                tries[k] += 1
                hits[k] += any(abs(m - x) <= LINE_RADIUS for m in changed)
    names = {0: "the commented line"}
    real = hits[0] / tries[0] if tries[0] else 0
    return [
        [
            names.get(k, f"{k} lines above"),
            pct(hits[k], tries[k]),
            f"{hits[k] / tries[k] / real:.2f}" if k and tries[k] and real else "",
            tries[k],
        ]
        for k in (0, 10, 25, 50, 100)
    ]


def main(db: str, summary_path: str, out: str) -> None:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    q = lambda s, *a: conn.execute(s, a).fetchall()  # noqa: E731
    # the selected flag follows the current widening step; count the projects that have threads
    projects = q("SELECT count(DISTINCT project_id) FROM threads WHERE substantive=1")[0][0]
    active = q("SELECT count(DISTINCT project_id) FROM merge_requests")[0][0]
    visible = q("SELECT count(*) FROM projects")[0][0]
    mrs = q("SELECT count(*) FROM merge_requests")[0][0]
    threads = q("SELECT count(*) FROM threads WHERE substantive=1")[0][0]
    cls = dict(q("SELECT status, count(*) FROM classifications GROUP BY 1"))
    prov = q(
        "SELECT model, prompt_version, count(*) FROM classifications WHERE status='ok' "
        "GROUP BY 1, 2 ORDER BY 3 DESC"
    )
    findings = q("SELECT outcome, verification, actionability, intent FROM findings")
    n = len(findings)
    outc = Counter(f[0] for f in findings)
    ver = Counter(f[1] for f in findings)
    act = [f for f in findings if f[2] == "change_request"]
    verified = sum(
        1
        for f in act
        if f[0] in ("implemented", "alternative_implemented", "partially_implemented")
        and f[1] == "direct"
    )
    intents = Counter(f[3] for f in findings)
    with open(summary_path, encoding="utf-8") as fh:
        summary = json.load(fh)
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    outcome_rows = [(k, outc.get(k, 0), OUTCOME_TIPS[k]) for k in OUTCOME_TIPS]
    ver_rows = [(k, v, "How the stated outcome is backed by code.") for k, v in ver.most_common()]
    intent_rows = [(k, v, "What the finding is about (LLM).") for k, v in intents.most_common()]
    qual = summary["quality"]
    dims = ["intent", "actionability", "validity", "primary_response", "text_outcome"]
    qual_rows = [[d] + [qual[c][d] for c in summary["quality_columns"]] for d in dims]
    done = summary["done"]
    kpis = [
        (
            "Projects with review threads",
            f"{projects}",
            f"of {active} active projects ({visible} visible)",
        ),
        ("Merge requests", f"{mrs:,}", "full history of the active projects"),
        ("Review threads classified", f"{cls.get('ok', 0):,}", f"of {threads:,} substantive"),
        ("Findings", f"{n:,}", "classified issues"),
        (
            "Verified remediation",
            pct(verified, len(act)),
            f"{verified:,} of {len(act):,} change requests",
        ),
        (
            "Open findings",
            pct(outc.get("open", 0), n),
            f"{outc.get('open', 0):,} findings, recent ones on open MRs included",
        ),
    ]
    kpi_html = "".join(
        f'<div class="kpi" title="{esc(s)}"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div><div class="s">{esc(s)}</div></div>'
        for k, v, s in kpis
    )
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>mrreview: final report</title><style>
:root{{--ink:#1d2433;--mut:#5b6478;--line:#e3e6ee;--bg:#fff;--card:#f7f8fb;--acc:#2f6fdf}}
@media (prefers-color-scheme:dark){{:root{{--ink:#e8ebf2;--mut:#a3abbd;--line:#30374a;--bg:#141823;--card:#1c2130;--acc:#6f9cf0}}}}
body{{font:15px/1.5 system-ui,sans-serif;color:var(--ink);background:var(--bg);max-width:1100px;margin:2rem auto;padding:0 1.2rem}}
h1{{margin:.2rem 0}} h2{{margin-top:2.2rem;border-bottom:1px solid var(--line);padding-bottom:.3rem}}
.sub{{color:var(--mut)}} .kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem;margin-top:1rem}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:.8rem 1rem}}
.kpi .k{{color:var(--mut);font-size:.85rem}} .kpi .v{{font-size:1.7rem;font-weight:650}} .kpi .s{{color:var(--mut);font-size:.85rem}}
.bars .row{{display:grid;grid-template-columns:220px 1fr 150px;gap:.6rem;align-items:center;margin:.25rem 0}}
.track{{background:var(--card);border-radius:4px;height:14px;display:block}} .bar{{display:block;height:14px;background:var(--acc);border-radius:0 4px 4px 0}}
.val{{font-variant-numeric:tabular-nums}} small{{color:var(--mut)}}
table{{border-collapse:collapse;width:100%;margin:.6rem 0;font-variant-numeric:tabular-nums}}
th,td{{border-bottom:1px solid var(--line);padding:.35rem .5rem;text-align:left}} th{{color:var(--mut);font-weight:600}}
ul li{{margin:.2rem 0}} .note{{color:var(--mut);font-size:.9rem}}
</style></head><body>
<h1>mrreview: final report</h1>
<div class="sub">GitLab review analytics with a local LLM. Generated {esc(now)} from the database. Aggregates only: no person and no project names.</div>
<div class="kpis">{kpi_html}</div>

<h2>Outcomes of the findings</h2>
<p class="note">Outcome = stated text outcome checked against the code. Hover a row for its meaning.</p>
{bars(outcome_rows, n)}
<h2>Code evidence behind the outcomes</h2>
{bars(ver_rows, n)}
<h2>What the findings are about</h2>
{bars(intent_rows, n)}

<h2>Classification quality (agreement with Claude Opus labels, kappa in brackets)</h2>
<p class="note">{esc(summary["quality_note"])}</p>
{table(["Dimension", *summary["quality_columns"]], qual_rows)}

<h2>Placebo check of the direct-evidence rule</h2>
<p class="note">Same rule (a change within {LINE_RADIUS} lines) applied to lines shifted away from the comment. Chance share = placebo rate divided by the rate at the commented line.</p>
{table(["Line tested", "Hit rate", "Chance share of a direct hit", "Tests"], placebo(conn))}
<p class="note">Limit: comments sit on lines that the MR already edits, and such lines change again more often. The placebo lines share this only partly, so the chance share is a lower bound.</p>

<h2>Comparison with published studies</h2>
{table(["Question", "Microsoft (Czerwonka et al. 2015)", "This run"], [
    ["Findings about a possible defect", "about 15%", pct(intents.get("defect", 0), n)],
    ["Findings about maintainability (style, design, maintainability)", "at least 50%",
     pct(sum(intents.get(k, 0) for k in ("style", "design", "maintainability")), n)],
])}

<h2>Provenance</h2>
{table(["Model", "Prompt", "Threads"], [list(r) for r in prov])}

<h2>What was done</h2>
<ul>{"".join(f"<li>{esc(x)}</li>" for x in done)}</ul>

<h2>Limits</h2>
<ul>{"".join(f"<li>{esc(x)}</li>" for x in summary["limits"])}</ul>
</body></html>"""
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"wrote {out}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
