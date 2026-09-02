"""The HTML report.

One self-contained file: inline CSS, no scripts, no external assets, no CDN. It
opens from the filesystem and survives being mailed to somebody who has no
access to this machine.

Charts are plain HTML bars rather than SVG — they reflow, they never overflow,
and the numbers stay selectable text. Magnitude is encoded with a single blue
ramp; the two composition bars use an ordinal ramp with a legend and direct
labels, so identity is never carried by colour alone.
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from typing import Any

from .stats import Survey, plural

STYLE = """
:root {
  color-scheme: light;
  --surface-0: #f6f5f2;
  --surface-1: #fcfcfb;
  --surface-2: #f0efec;
  --border: #dcdbd5;
  --text-primary: #0b0b0b;
  --text-secondary: #52514e;
  --text-muted: #7a7873;
  --seq-1: #184f95;
  --seq-2: #256abf;
  --seq-3: #3987e5;
  --seq-4: #86b6ef;
  --accent: #2a78d6;
  --good: #1baf7a;
  --warn: #eda100;
  --risk: #e34948;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --surface-0: #121211;
    --surface-1: #1a1a19;
    --surface-2: #252523;
    --border: #3a3a37;
    --text-primary: #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted: #93918a;
    --seq-1: #86b6ef;
    --seq-2: #5598e7;
    --seq-3: #3987e5;
    --seq-4: #184f95;
    --accent: #3987e5;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-0: #121211;
  --surface-1: #1a1a19;
  --surface-2: #252523;
  --border: #3a3a37;
  --text-primary: #ffffff;
  --text-secondary: #c3c2b7;
  --text-muted: #93918a;
  --seq-1: #86b6ef;
  --seq-2: #5598e7;
  --seq-3: #3987e5;
  --seq-4: #184f95;
  --accent: #3987e5;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--surface-0);
  color: var(--text-primary);
  font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
.wrap { max-width: 1080px; margin: 0 auto; padding: 40px 24px 80px; }
header { border-bottom: 1px solid var(--border); padding-bottom: 24px; margin-bottom: 32px; }
h1 { font-size: 30px; line-height: 1.2; margin: 0 0 8px; letter-spacing: -0.02em; }
h2 { font-size: 20px; margin: 44px 0 6px; letter-spacing: -0.01em; }
h3 { font-size: 15px; margin: 26px 0 8px; color: var(--text-secondary); font-weight: 600; }
p { margin: 8px 0; color: var(--text-secondary); max-width: 74ch; }
.lede { color: var(--text-muted); font-size: 13px; }
code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
code { background: var(--surface-2); padding: 1px 5px; border-radius: 4px; font-size: 0.9em; }

.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 24px 0 8px; }
.tile { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
.tile .value { font-size: 27px; font-weight: 650; letter-spacing: -0.02em; }
.tile .label { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.tile .sub { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }

.chart { margin: 14px 0 8px; }
.row { display: grid; grid-template-columns: minmax(120px, 240px) 1fr auto; gap: 12px; align-items: center; padding: 3px 0; }
.row .name { font-size: 13px; color: var(--text-secondary); text-align: right; overflow-wrap: anywhere; }
.row .track { background: var(--surface-2); border-radius: 4px; height: 15px; position: relative; }
.row .bar { height: 15px; border-radius: 0 4px 4px 0; background: var(--seq-3); min-width: 2px; }
.row .bar.rank-1 { background: var(--seq-1); }
.row .bar.rank-2 { background: var(--seq-2); }
.row .num { font-size: 12px; color: var(--text-muted); font-variant-numeric: tabular-nums; min-width: 74px; }
.row:hover .name, .row:hover .num { color: var(--text-primary); }

.stack { display: flex; gap: 2px; height: 26px; margin: 10px 0 6px; }
.stack > span { display: flex; align-items: center; justify-content: center; font-size: 11px; color: #fff; }
.stack > span:first-child { border-radius: 4px 0 0 4px; }
.stack > span:last-child { border-radius: 0 4px 4px 0; }
.legend { display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }

.finding { background: var(--surface-1); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: 8px; padding: 14px 16px; margin: 12px 0; }
.finding.risk { border-left-color: var(--risk); }
.finding.inconsistency { border-left-color: var(--warn); }
.finding.insight { border-left-color: var(--good); }
.finding .tag { font-size: 11px; text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-muted); font-weight: 700; }
.finding h4 { margin: 4px 0 6px; font-size: 16px; }
.finding p { margin: 0 0 8px; font-size: 14px; }
.finding ul { margin: 0; padding-left: 18px; color: var(--text-muted); font-size: 13px; }
.finding li { margin: 2px 0; overflow-wrap: anywhere; }

table { width: 100%; border-collapse: collapse; font-size: 13px; margin: 10px 0; }
th { text-align: left; font-weight: 600; color: var(--text-muted); font-size: 12px; border-bottom: 1px solid var(--border); padding: 6px 8px; }
td { border-bottom: 1px solid var(--border); padding: 6px 8px; color: var(--text-secondary); vertical-align: top; }
td.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
tr:hover td { color: var(--text-primary); background: var(--surface-1); }
.scroll { overflow-x: auto; }

pre.doc { background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px; padding: 16px; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 12.5px; line-height: 1.5; color: var(--text-secondary); }
footer { margin-top: 56px; padding-top: 20px; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 12px; }
"""


def _esc(text: Any) -> str:
    return html.escape(str(text))


def _bar_rows(rows: Sequence[tuple[str, float, str]], maximum: float | None = None) -> str:
    """Horizontal bars: label, magnitude, printed value. One hue, ranked shades."""
    if not rows:
        return "<p class='lede'>Nothing to show.</p>"
    top = maximum if maximum is not None else max(value for _, value, _ in rows) or 1
    out = ["<div class='chart'>"]
    for index, (name, value, printed) in enumerate(rows):
        width = max(0.6, value / top * 100)
        rank = f" rank-{index + 1}" if index < 2 else ""
        out.append(
            f"<div class='row' title='{_esc(name)}: {_esc(printed)}'>"
            f"<div class='name'>{_esc(name)}</div>"
            f"<div class='track'><div class='bar{rank}' style='width:{width:.1f}%'></div></div>"
            f"<div class='num'>{_esc(printed)}</div></div>"
        )
    out.append("</div>")
    return "".join(out)


def _stack(parts: list[tuple[str, int, str]]) -> str:
    """A single composition bar with a legend and in-bar direct labels."""
    total = sum(count for _, count, _ in parts) or 1
    legend = "".join(
        f"<span><i style='background:{colour}'></i>{_esc(label)} — {count:,} ({count/total:.0%})</span>"
        for label, count, colour in parts
        if count
    )
    segments = "".join(
        f"<span style='background:{colour};flex:{count}' title='{_esc(label)}: {count:,} ({count/total:.0%})'>"
        f"{f'{count/total:.0%}' if count / total > 0.07 else ''}</span>"
        for label, count, colour in parts
        if count
    )
    return f"<div class='legend'>{legend}</div><div class='stack'>{segments}</div>"


TITLE = "The AGENTS.md Census"


def _body(survey: Survey, canonical: str) -> str:
    """The page markup, without a document wrapper."""
    head = survey.headline()
    findings = survey.findings or survey.compute_findings()
    topics = survey.topic_table()
    scopes = survey.scope_summaries()
    total_scopes = head["scopes"] or 1

    # --- tiles -------------------------------------------------------------
    tiles = [
        (f"{head['repos_scanned']}", "repositories scanned", f"{head['repos_seen'] - head['repos_scanned']} nested checkouts excluded"),
        (
            f"{head['cov_active_instructed']}/{head['cov_active_repos']}",
            "active repositories instructed",
            f"{head['cov_active_share']:.0%} of those committed to in the last "
            f"{head['cov_active_days']} days",
        ),
        (
            f"{head['cov_active_with_agents_md']}/{head['cov_active_repos']}",
            "have an AGENTS.md",
            f"{head['cov_active_agents_md_share']:.0%} — the rest is CLAUDE.md, skills or config",
        ),
        (
            f"{head['files_first_party']}",
            "first-party instruction files",
            f"in {head['scopes']} scopes · {head['files_excluded']} vendored or duplicate, excluded",
        ),
        (f"{head['directives']:,}", "atomic directives", f"{head['classified_share']:.0%} matched by the lexicon"),
        (f"{head['total_tokens']:,}", "tokens of instructions", f"median scope {head['median_bytes'] // 4:,} tokens"),
    ]
    tile_html = "".join(
        f"<div class='tile'><div class='value'>{_esc(v)}</div>"
        f"<div class='label'>{_esc(label)}</div><div class='sub'>{_esc(sub)}</div></div>"
        for v, label, sub in tiles
    )

    # --- findings ----------------------------------------------------------
    finding_html = "".join(
        f"<div class='finding {_esc(f.severity)}'>"
        f"<div class='tag'>{_esc(f.severity)}</div>"
        f"<h4>{_esc(f.title)}</h4><p>{_esc(f.detail)}</p>"
        + ("<ul>" + "".join(f"<li>{_esc(e)}</li>" for e in f.evidence) + "</ul>" if f.evidence else "")
        + "</div>"
        for f in findings
    )

    # --- topic frequency ---------------------------------------------------
    topic_rows = [
        (row["label"], row["scopes"], f"{row['scopes']} of {total_scopes} · {row['share']:.0%}")
        for row in topics[:26]
    ]

    # --- topic groups ------------------------------------------------------
    group_scopes: dict[str, set[str]] = {}
    for row in topics:
        group_scopes.setdefault(row["group"], set()).update(row["scope_names"])
    group_rows = sorted(
        ((g, len(s), f"{len(s)} of {total_scopes}") for g, s in group_scopes.items()),
        key=lambda r: -r[1],
    )

    # --- context budget ----------------------------------------------------
    budget = sorted(scopes, key=lambda s: -s.tokens)[:15]
    budget_rows = [(s.scope, s.tokens, f"{s.tokens:,} tok · {s.directives} rules") for s in budget]

    # --- composition -------------------------------------------------------
    hardness = _stack(
        [
            ("Binding (must / never / always)", head["hard_directives"], "var(--seq-1)"),
            ("Advisory (should / prefer)", head["soft_directives"], "var(--seq-3)"),
            (
                "Unmarked",
                head["directives"] - head["hard_directives"] - head["soft_directives"],
                "var(--seq-4)",
            ),
        ]
    )
    roles: dict[str, int] = {}
    for item in survey.first_party:
        doc = survey.parsed.get(item.path)
        if doc is None:
            continue
        for section in doc.sections:
            roles[section.role] = roles.get(section.role, 0) + 1
    role_stack = _stack(
        [
            ("Rules", roles.get("rules", 0), "var(--seq-1)"),
            ("Project description", roles.get("description", 0), "var(--seq-2)"),
            ("Command cheat-sheet", roles.get("commands", 0), "var(--seq-3)"),
            ("Reference material", roles.get("reference", 0), "var(--seq-4)"),
        ]
    )

    # --- naming and placement ---------------------------------------------
    names: dict[str, int] = {}
    places: dict[str, int] = {}
    for item in survey.first_party:
        if item.kind != "agents_md":
            continue
        names[item.name] = names.get(item.name, 0) + 1
        places[item.location] = places.get(item.location, 0) + 1
    name_rows = [(n, c, plural(c, "file")) for n, c in sorted(names.items(), key=lambda kv: -kv[1])]
    place_labels = {"root": "repository root", "docs": "docs/ or documents/", "nested": "a nested subdirectory", "dot-dir": "a dot-directory"}
    place_rows = [
        (place_labels.get(p, p), c, plural(c, "file"))
        for p, c in sorted(places.items(), key=lambda kv: -kv[1])
    ]

    # --- repeated wordings -------------------------------------------------
    repeated = survey.repeated_directives()[:14]
    repeated_html = "".join(
        f"<tr><td class='n'>{len(r['scopes'])}</td><td>{_esc(r['text'][:190])}</td>"
        f"<td>{_esc(', '.join(r['scopes'][:4]))}</td></tr>"
        for r in repeated
    )

    # --- scope table -------------------------------------------------------
    scope_html = "".join(
        f"<tr><td>{_esc(s.scope)}</td><td class='n'>{len(s.files)}</td>"
        f"<td class='n'>{s.tokens:,}</td><td class='n'>{s.directives}</td>"
        f"<td class='n'>{s.hard}</td><td class='n'>{len(s.topics)}</td>"
        f"<td>{_esc(s.last_commit_date or '—')}</td></tr>"
        for s in sorted(scopes, key=lambda s: -s.directives)
    )

    # --- topic table -------------------------------------------------------
    topic_table_html = "".join(
        f"<tr><td>{_esc(r['group'])}</td><td>{_esc(r['label'])}</td>"
        f"<td class='n'>{r['scopes']}</td><td class='n'>{r['share']:.0%}</td>"
        f"<td class='n'>{r['directives']}</td>"
        f"<td>{_esc(', '.join(r['scope_names'][:5]))}{'…' if len(r['scope_names']) > 5 else ''}</td></tr>"
        for r in topics
    )

    return f"""<div class="wrap">
<header>
  <h1>What my agent instruction files actually say</h1>
  <p>A census of every <code>AGENTS.md</code>, <code>CLAUDE.md</code>, skill and harness
     config under <code>{_esc(head['root'])}</code> — what exists, what recurs, and what
     the house standard would be if it were written down.</p>
  <p class="lede">Generated {_esc(head['generated'])} · taxonomy v{_esc(head['taxonomy_version'])} ·
     every number below is computed deterministically from the files themselves.</p>
</header>

<div class="tiles">{tile_html}</div>

<h2>Findings</h2>
<p>Each statement carries the evidence it was derived from.</p>
{finding_html}

<h2>What the instructions are about</h2>
<p>How many independent scopes state a rule on each topic. Scopes, not sentences:
   one verbose repository repeating itself must not outvote three quietly agreeing.</p>
{_bar_rows(topic_rows, maximum=total_scopes)}

<h3>By theme</h3>
{_bar_rows(group_rows, maximum=total_scopes)}

<h2>How binding the language is</h2>
<p>Binding wording is what an agent is most likely to actually obey. Most of the
   corpus is neither — it is description in the same file as the rules.</p>
{hardness}

<h3>What the sections are doing</h3>
<p>Three different documents share one filename. Only the rules generalise between
   repositories; description and command lists are why these files cannot simply be copied.</p>
{role_stack}

<h2>The context budget</h2>
<p>Every session in a scope pays for its instruction file before any work happens.</p>
{_bar_rows(budget_rows)}

<h2>Where the files live and what they are called</h2>
<div class="scroll">{_bar_rows(name_rows)}</div>
{_bar_rows(place_rows)}

<h2>Wordings carried between repositories</h2>
<p>The same sentence, normalized, appearing in more than one scope — the strongest
   available evidence of a house style, because somebody copied it by hand.</p>
<div class="scroll"><table>
<thead><tr><th>Scopes</th><th>Directive</th><th>Where</th></tr></thead>
<tbody>{repeated_html}</tbody></table></div>

<h2>The synthesized house standard</h2>
<p>Built from the rules that recur, each line quoting wording already in service and
   carrying the scope count that justifies it. Written alongside this report as
   <code>AGENTS.canonical.md</code>.</p>
<pre class="doc">{_esc(canonical)}</pre>

<h2>Every scope</h2>
<div class="scroll"><table>
<thead><tr><th>Scope</th><th>Files</th><th>Tokens</th><th>Directives</th><th>Binding</th><th>Topics</th><th>Last touched</th></tr></thead>
<tbody>{scope_html}</tbody></table></div>

<h2>Every topic</h2>
<div class="scroll"><table>
<thead><tr><th>Theme</th><th>Topic</th><th>Scopes</th><th>Share</th><th>Directives</th><th>Where</th></tr></thead>
<tbody>{topic_table_html}</tbody></table></div>

<footer>
  <p>AgentsMdSurvey · collection and segmentation are deterministic; classification is a
     versioned lexicon plus an optional cached semantic pass. The model may label, cluster
     and phrase — it never counts. {head['directives'] - head['directives_classified']:,} of
     {head['directives']:,} directives fell outside the lexicon and are the tail the semantic
     pass exists for.</p>
</footer>
</div>
"""


def render(survey: Survey, canonical: str) -> str:
    """A standalone HTML file that opens from the filesystem."""
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{TITLE}</title>\n<style>{STYLE}</style>\n</head>\n<body>\n"
        + _body(survey, canonical)
        + "</body>\n</html>\n"
    )


def render_fragment(survey: Survey, canonical: str) -> str:
    """Title, styles and markup for a host that supplies its own document shell."""
    return f"<title>{TITLE}</title>\n<style>{STYLE}</style>\n" + _body(survey, canonical)
