#!/usr/bin/env python3
"""Generate the A4 one-pager (HTML + PDF) from the files in data/.

Never edit onepager.html by hand: change the data or this script, then re-run.
Measured values come from the scripts' output; forum facts come from data/status.json.
Usage: python3 make_onepager.py [--today YYYY-MM-DD] [--no-pdf]
"""
import argparse
import csv
import html
import json
import math
import re
import shutil
import statistics
import subprocess
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

BLUE, ORANGE = "#2a78d6", "#eb6834"  # series-1 Manjaro stable, series-2 Manjaro unstable
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
LAG_PACKAGES = ("linux71", "linux72", "plasma-desktop", "mesa", "systemd", "firefox")
BRANCHES = ("arch", "unstable", "testing", "stable")


def d(s):
    return date.fromisoformat(s)


def latest(pattern):
    files = sorted(DATA.glob(pattern))
    if not files:
        raise SystemExit(f"Missing data file: data/{pattern}")
    return files[-1]


def load_announcements():
    with open(DATA / "stable_announcements.csv", newline="") as f:
        return [dict(r, date=d(r["date"])) for r in csv.DictReader(f)]


def load_upstream():
    with open(DATA / "upstream_calendar.csv", newline="") as f:
        return list(csv.DictReader(f))


def load_status():
    return json.loads((DATA / "status.json").read_text())


def load_local():
    """Return (waves [(date, n)], months {YYYY-MM: n}) from measure_local_waves.sh output."""
    txt = latest("local_waves_*.txt").read_text()
    waves = [(d(a), int(b)) for a, b in re.findall(r"^\s+(\d{4}-\d\d-\d\d)\s+(\d+) pkgs", txt, re.M)]
    months = {a: int(b) for a, b in re.findall(r"^\s+(\d{4}-\d\d)\s+(\d+)$", txt, re.M)}
    if not waves:
        raise SystemExit("No waves in local_waves data")
    return waves, months


def load_branch_lag():
    """Parse the tab-separated sections of measure_branch_lag.sh output."""
    rows, weeks, section = [], {}, None
    for line in latest("branch_lag_*.txt").read_text().splitlines():
        if line.startswith("## "):
            section = line[3:].split()[0]
            continue
        if not line.strip():
            continue
        f = line.split("\t")
        if section == "versions":
            rows.append((f[0], dict(zip(BRANCHES, f[1:]))))
        elif section == "builds":
            weeks.setdefault(f[0], []).append((f[1], int(f[2])))
    if not rows or "stable" not in weeks:
        raise SystemExit("branch_lag data is incomplete")
    return rows, weeks


def cell_parts(cell):
    m = re.match(r"(\S+) \((\d{4}-\d\d-\d\d)\)", cell)
    return (re.sub(r"^\d+:", "", m[1]).rsplit("-", 1)[0], d(m[2])) if m else None


# ---------- SVG helpers ----------

def esc(s):
    return html.escape(str(s), quote=True)


def text(x, y, s, size=9, fill=INK2, anchor="start", weight=400):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{esc(s)}</text>')


def bar(x, y0, w, h, fill, tip, extra=""):
    """Vertical bar anchored on baseline y0, 2px rounded top, with a hover tooltip."""
    h = max(h, 1)
    r = min(2, w / 2, h)
    p = (f"M{x:.1f},{y0:.1f} V{y0 - h + r:.1f} Q{x:.1f},{y0 - h:.1f} {x + r:.1f},{y0 - h:.1f} "
         f"H{x + w - r:.1f} Q{x + w:.1f},{y0 - h:.1f} {x + w:.1f},{y0 - h + r:.1f} V{y0:.1f} Z")
    return f'<path d="{p}" fill="{fill}" {extra}><title>{esc(tip)}</title></path>'


def nice_max(v, step):
    return max(step, math.ceil(v * 1.05 / step) * step)


def grid(out, L, R, W, y, ticks):
    for v in ticks:
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{GRID}" stroke-width="0.6"/>')
        out.append(text(L - 4, y(v) + 3, v, 8, MUTED, "end"))


def gap_chart(ann, gaps, open_gap, med, today, W=700, H=132):
    """Bars at each stable update date; height = days since the previous update."""
    L, R, T, B = 34, 80, 14, 22
    start, end = date(ann[0]["date"].year, 1, 1), today + timedelta(days=10)
    span = (end - start).days
    x = lambda dt: L + (dt - start).days / span * (W - L - R)
    ymax = nice_max(max([open_gap] + [g for _, g, _ in gaps]), 40)
    y = lambda v: H - B - v / ymax * (H - T - B)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Days between Manjaro stable updates">',
           '<defs><pattern id="hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           f'<line x1="0" y1="0" x2="0" y2="4" stroke="{BLUE}" stroke-width="1.6"/></pattern></defs>']
    grid(out, L, R, W, y, range(0, ymax + 1, 40))
    out.append(text(4, T - 4, "days", 8, MUTED))
    m = start
    while m <= end:
        if m.month in (1, 4, 7, 10):
            out.append(text(x(m), H - 8, m.strftime("%b %Y" if m.month == 1 else "%b"), 8, MUTED, "middle"))
        m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    bw = 5
    for dt, g, title in gaps:
        out.append(bar(x(dt) - bw / 2, y(0), bw, y(0) - y(g), BLUE, f"{dt}: {g} d since previous update — {title}"))
    ox = x(today) - bw / 2
    out.append(bar(ox, y(0), bw, y(0) - y(open_gap), "url(#hatch)",
                   f"{today}: {open_gap} d since {ann[-1]['date']} and still open", f'stroke="{BLUE}" stroke-width="1"'))
    out.append(text(ox + bw + 4, y(open_gap) + 3, f"{open_gap} d, still open", 9, INK, weight=700))
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(med):.1f}" y2="{y(med):.1f}" stroke="{INK2}" stroke-width="1" stroke-dasharray="3 3"/>')
    out.append(text(W - R + 4, y(med) + 3, f"median {med:g} d (all)", 8, INK2))
    longest = max(gaps, key=lambda t: t[1])
    out.append(text(x(longest[0]) + 5, y(longest[1]) + 3, f"{longest[1]} d (to {longest[0]:%d %b %Y})", 8, INK2))
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(0)}" y2="{y(0)}" stroke="{MUTED}" stroke-width="0.8"/>')
    out.append("</svg>")
    return "".join(out)


def week_chart(weeks, W=340, H=118):
    """Grouped bars per ISO week: Manjaro unstable vs stable, one shared axis (same unit)."""
    L, R, T, B = 34, 6, 10, 22
    uns, stab = dict(weeks["unstable"]), dict(weeks["stable"])
    labels = sorted(set(uns) | set(stab))[-8:]
    ymax = nice_max(max(list(uns.values()) + list(stab.values())), 1000)
    y = lambda v: H - B - v / ymax * (H - T - B)
    slot = (W - L - R) / len(labels)
    bw = (slot - 8) / 2
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Packages built per week, Manjaro unstable vs stable">']
    grid(out, L, R, W, y, range(0, ymax + 1, 1000))
    for i, wk in enumerate(labels):
        x0 = L + i * slot + 3
        u, s = uns.get(wk, 0), stab.get(wk, 0)
        out.append(bar(x0, y(0), bw, y(0) - y(u), ORANGE, f"{wk} unstable: {u} packages"))
        out.append(bar(x0 + bw + 2, y(0), bw, y(0) - y(s), BLUE, f"{wk} stable: {s} packages"))
        if s < ymax * 0.1:
            out.append(text(x0 + bw + 2 + bw / 2, y(s) - 3, s, 7, INK2, "middle"))
        out.append(text(x0 + slot / 2 - 3, H - 8, wk[-3:], 8, MUTED, "middle"))
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(0)}" y2="{y(0)}" stroke="{MUTED}" stroke-width="0.8"/>')
    out.append("</svg>")
    return "".join(out), labels


def local_chart(waves, today, W=340, H=118):
    """Packages upgraded on this laptop per update-wave day."""
    L, R, T, B = 34, 6, 10, 22
    start = date(waves[0][0].year, waves[0][0].month, 1)
    end = today + timedelta(days=5)
    span = (end - start).days
    x = lambda dt: L + (dt - start).days / span * (W - L - R)
    ymax = nice_max(max(n for _, n in waves), 500)
    y = lambda v: H - B - v / ymax * (H - T - B)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Packages upgraded per update wave on this laptop">']
    grid(out, L, R, W, y, range(0, ymax + 1, 500))
    m = start
    while m <= end:
        if m.month in (1, 4, 7, 10):
            out.append(text(x(m), H - 8, m.strftime("%b %y"), 8, MUTED, "middle"))
        m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    for dt, n in waves:
        out.append(bar(x(dt) - 2.5, y(0), 5, y(0) - y(n), BLUE, f"{dt}: {n} packages upgraded"))
    out.append(f'<line x1="{x(today):.1f}" x2="{x(today):.1f}" y1="{T}" y2="{y(0)}" stroke="{INK2}" stroke-dasharray="2 2"/>')
    out.append(text(x(today) - 3, T + 8, "today", 8, INK2, "end"))
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(0)}" y2="{y(0)}" stroke="{MUTED}" stroke-width="0.8"/>')
    out.append("</svg>")
    return "".join(out)


def lag_table(rows, today):
    head = "<tr><th>package</th>" + "".join(f"<th>{b}</th>" for b in BRANCHES) + "</tr>"
    body = []
    for name, cells in rows:
        tds = []
        for br in BRANCHES:
            p = cell_parts(cells.get(br, "-"))
            if not p:
                tds.append('<td class="na">–</td>')
                continue
            age = (today - p[1]).days
            tds.append(f'<td class="{"old" if age > 30 else ""}"><b>{esc(p[0])}</b> <span>{age} d</span></td>')
        body.append(f"<tr><td class='pk'>{esc(name)}</td>{''.join(tds)}</tr>")
    return f"<table class='lag'>{head}{''.join(body)}</table>"


def median_age(rows, br, today):
    """Median build age in days over the table rows; skip linuxNN rows absent from Arch."""
    ages = [(today - p[1]).days for name, c in rows
            if not re.fullmatch(r"linux\d+", name) and (p := cell_parts(c.get(br, "-")))]
    return statistics.median(ages) if ages else None


def build(today):
    ann = load_announcements()
    status = load_status()
    waves, months = load_local()
    lag_rows, weeks = load_branch_lag()
    upstream = load_upstream()

    gaps = [(a["date"], (a["date"] - p["date"]).days, a["title"]) for p, a in zip(ann, ann[1:])]
    open_gap = (today - ann[-1]["date"]).days
    med_all = statistics.median(g for _, g, _ in gaps)
    gaps_year = [g for dt, g, _ in gaps if dt.year == today.year]
    longer = sum(1 for _, g, _ in gaps if g >= open_gap)
    wave_gaps = [(b[0] - a[0]).days for a, b in zip(waves, waves[1:])]
    last_wave = waves[-1][0]
    month_now = months.get(today.strftime("%Y-%m"), 0)

    lag_rows = [r for r in lag_rows if r[0] in LAG_PACKAGES]
    ages = {br: median_age(lag_rows, br, today) for br in BRANCHES}
    age_note = ", ".join(f"{br} {ages[br]:g} d" for br in BRANCHES if ages[br] is not None)

    wsvg, wlabels = week_chart(weeks)
    ann_week = ann[-1]["date"].strftime("%G-W%V")
    stab = dict(weeks["stable"])
    quiet = [wk for wk in wlabels if wk > ann_week]
    quiet_txt = ", ".join(f"{wk[-3:]} {stab.get(wk, 0)}" for wk in quiet)

    year_stats = (f"{statistics.median(gaps_year):g} d", f"median gap in {today.year} ({len(gaps_year)} gaps, "
                  f"range {min(gaps_year)}–{max(gaps_year)} d)") if gaps_year else ("–", f"no gaps in {today.year}")
    up_rows = "".join(f"<tr><td class='pk'>{esc(u['upstream'])}</td><td>{esc(u['rhythm'])}</td>"
                      f"<td class='nw'>{esc(u['last'])}</td><td class='nw'>{esc(u['next'])}</td></tr>" for u in upstream)
    reasons = "".join(f"<li>{esc(r)}</li>" for r in status["reasons"])
    frozen = status.get("freeze")
    slowed = ("did not slow down" if gaps_year and statistics.median(gaps_year) <= med_all * 1.25 else "slowed down")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manjaro Update Cadence</title>
<style>
@page {{ size: A4; margin: 0; }}
:root {{ color-scheme: light; --ink:{INK}; --ink2:{INK2}; --muted:{MUTED}; --grid:{GRID};
  --blue:{BLUE}; --orange:{ORANGE}; --surface:#fcfcfb; --card:#f3f2ef; --crit:#c93b3a; }}
* {{ box-sizing: border-box; }}
html, body {{ margin:0; background:#dcdbd7; }}
body {{ font: 9pt/1.35 "Inter", "Noto Sans", "DejaVu Sans", sans-serif; color: var(--ink); }}
.page {{ width:210mm; height:297mm; margin:0 auto; background:var(--surface); padding:9mm 11mm 7mm;
  display:flex; flex-direction:column; gap:2.4mm; overflow:hidden; }}
@media print {{ html, body {{ background:var(--surface); }} .page {{ margin:0; }} }}
@media screen and (max-width: 820px) {{ .page {{ width:auto; height:auto; padding:16px; }} .row {{ flex-direction:column; }} .tiles {{ grid-template-columns:1fr 1fr; }} }}
header {{ display:flex; justify-content:space-between; align-items:flex-end; border-bottom:1.5px solid var(--ink); padding-bottom:2mm; }}
h1 {{ font-size:18pt; margin:0; letter-spacing:-0.3px; }}
h1 small {{ display:block; font-size:9pt; font-weight:400; color:var(--ink2); letter-spacing:0; }}
.meta {{ text-align:right; color:var(--ink2); font-size:8pt; }}
h2 {{ font-size:9.5pt; margin:0 0 1mm; }}
h2 span {{ font-weight:400; color:var(--ink2); }}
.row {{ display:flex; gap:4mm; }}
.row > * {{ flex:1; min-width:0; }}
.tiles {{ display:grid; grid-template-columns: 1.25fr 1fr 1fr 1fr; gap:3mm; }}
.tile {{ background:var(--card); border-radius:2mm; padding:2.2mm 3mm; }}
.tile .v {{ font-size:19pt; font-weight:700; line-height:1.1; }}
.tile .l {{ color:var(--ink2); font-size:8pt; }}
.tile.alert {{ background:#fbe9e8; }}
.tile.alert .v {{ color:var(--crit); font-size:15pt; }}
.legend {{ font-size:8pt; color:var(--ink2); display:flex; gap:4mm; margin:0 0 1mm; }}
.sw {{ display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:4px; vertical-align:0; }}
.hatch {{ background: repeating-linear-gradient(45deg, var(--blue) 0 1.2px, transparent 1.2px 3px); outline:1px solid var(--blue); }}
table {{ border-collapse:collapse; width:100%; font-size:8pt; }}
th {{ text-align:left; font-weight:600; color:var(--ink2); border-bottom:1px solid var(--muted); padding:0.6mm 1.2mm; }}
td {{ border-bottom:0.5px solid var(--grid); padding:0.6mm 1.2mm; vertical-align:top; }}
td.pk {{ font-weight:600; white-space:nowrap; }}
.lag td span {{ color:var(--muted); }}
.lag td.old {{ background:#eaf1fb; }}
.lag td.old span {{ color:var(--blue); font-weight:600; }}
td.na {{ color:var(--muted); }}
td.nw {{ white-space:nowrap; }}
ul, ol {{ margin:0; padding-left:4.5mm; }}
li {{ margin-bottom:0.6mm; }}
code {{ font: 7.5pt "JetBrains Mono", "DejaVu Sans Mono", monospace; background:var(--card); padding:0 1mm; border-radius:1mm; }}
.note {{ font-size:7.5pt; color:var(--ink2); }}
footer {{ margin-top:auto; font-size:7pt; color:var(--muted); border-top:0.5px solid var(--grid); padding-top:1.5mm; }}
</style></head>
<body><div class="page">

<header>
  <h1>When do Manjaro stable updates come?<small>Update rhythm, the current pause, and how to measure it yourself</small></h1>
  <div class="meta">As of {today:%Y-%m-%d}<br>Branch: stable · this laptop</div>
</header>

<section class="tiles">
  {f'<div class="tile alert"><div class="v">❄ FROZEN</div><div class="l">since {esc(frozen["since"])}. {esc(frozen["text"])}</div></div>' if frozen else '<div class="tile"><div class="v">running</div><div class="l">no freeze announced</div></div>'}
  <div class="tile"><div class="v">{open_gap} d</div><div class="l">since the last announced stable update ({ann[-1]['date']:%Y-%m-%d})</div></div>
  <div class="tile"><div class="v">{year_stats[0]}</div><div class="l">{year_stats[1]}</div></div>
  <div class="tile"><div class="v">{longer} of {len(gaps)}</div><div class="l">gaps since {ann[0]['date']:%Y-%m} were as long or longer than the current one.</div></div>
</section>

<section>
  <h2>Days between stable updates <span>· one bar per forum announcement, height = days since the previous one</span></h2>
  <div class="legend"><span><i class="sw" style="background:var(--blue)"></i>closed gap</span><span><i class="sw hatch"></i>current gap (still open)</span><span>- - - median of all gaps since {ann[0]['date']:%Y-%m}</span></div>
  {gap_chart(ann, gaps, open_gap, med_all, today)}
</section>

<section class="row">
  <div>
    <h2>Unstable moves, stable waits <span>· packages built per week</span></h2>
    <div class="legend"><span><i class="sw" style="background:var(--orange)"></i>Manjaro unstable</span><span><i class="sw" style="background:var(--blue)"></i>Manjaro stable</span></div>
    {wsvg}
    <div class="note">Counts only versions still in the repo, so older weeks look smaller. The last stable update came in {ann_week[-3:]}. Stable builds since then: {quiet_txt} (unannounced security fixes).</div>
  </div>
  <div>
    <h2>Update waves on this laptop <span>· days with ≥ 200 upgrades</span></h2>
    <div class="legend"><span><i class="sw" style="background:var(--blue)"></i>packages upgraded that day (from <code>pacman.log</code>)</span></div>
    {local_chart(waves, today)}
    <div class="note">Median gap between waves: {statistics.median(wave_gaps):g} d. Last wave: {last_wave:%Y-%m-%d}. Upgrades in {today:%B %Y} so far: {month_now}.</div>
  </div>
</section>

<section class="row">
  <div style="flex:1.15">
    <h2>Where the packages wait <span>· version, build age</span></h2>
    {lag_table(lag_rows, today)}
    <div class="note">Shaded = older than 30 days. Median build age (non-kernel rows): {age_note}.</div>
  </div>
  <div>
    <h2>Upstream rhythm <span>· what drives the waves</span></h2>
    <table><tr><th>upstream</th><th>rhythm</th><th>last</th><th>next</th></tr>{up_rows}</table>
    <div class="note">{esc(status['upstream_note'])}</div>
  </div>
</section>

<section class="row">
  <div>
    <h2>Verdict</h2>
    <ul>
      <li><b>Stable is paused, not slower.</b> Before the pause, the rhythm {slowed}: {year_stats[0]} median in {today.year}, {med_all:g} d overall.</li>
      {reasons}
      <li>{esc(status['next_update'])}</li>
      <li><b>Action:</b> {status['action']}</li>
    </ul>
  </div>
  <div>
    <h2>Measure it yourself</h2>
    <ol>
      <li>Read the stable announcements: <code>forum.manjaro.org/c/announcements/stable-updates/12.rss</code></li>
      <li>Check the date of the last branch change: <code>curl -s https://mirror.init7.net/manjaro/stable/state</code></li>
      <li>Compare branch versions: <code>./measure_branch_lag.sh</code></li>
      <li>Count your own update waves: <code>./measure_local_waves.sh</code></li>
      <li>Rebuild this page: <code>python3 make_onepager.py</code></li>
    </ol>
    <div class="note">The <code>state</code> date also changes for small security fixes. It is not proof of a full update.</div>
  </div>
</section>

<footer>Sources: forum.manjaro.org announcements (Discourse JSON), Manjaro and Arch repo databases (mirror.init7.net, geo.mirror.pkgbuild.com), kernel.org, KDE/Mesa/Firefox release calendars, local /var/log/pacman.log.
Generated by make_onepager.py from data/ in 20261022_manjaroLinuxUpdateFrequency. Hover a bar for its value.</footer>
</div></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()
    out = HERE / "onepager.html"
    out.write_text(build(d(a.today)))
    print(f"wrote {out}")
    if a.no_pdf:
        return
    browser = shutil.which("chromium") or shutil.which("google-chrome-stable")
    if not browser:
        raise SystemExit("No chromium found; HTML only.")
    pdf = HERE / "onepager.pdf"
    subprocess.run([browser, "--headless=new", "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                    out.as_uri()], check=True, capture_output=True)
    print(f"wrote {pdf}")


if __name__ == "__main__":
    main()
