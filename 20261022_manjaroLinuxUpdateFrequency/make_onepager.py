#!/usr/bin/env python3
"""Generate the A4 one-pager (HTML + PDF) from the files in data/.

Never edit onepager.html by hand: change the data or this script, then re-run.
Usage: python3 make_onepager.py [--today YYYY-MM-DD] [--no-pdf]
"""
import argparse
import csv
import html
import re
import shutil
import statistics
import subprocess
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

BLUE, ORANGE = "#2a78d6", "#eb6834"  # series-1 Manjaro stable, series-2 Arch
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"


def d(s):
    return date.fromisoformat(s)


def load_announcements():
    with open(DATA / "stable_announcements.csv", newline="") as f:
        return [dict(r, date=d(r["date"])) for r in csv.DictReader(f)]


def load_upstream():
    with open(DATA / "upstream_calendar.csv", newline="") as f:
        return list(csv.DictReader(f))


def latest(pattern):
    files = sorted(DATA.glob(pattern))
    if not files:
        raise SystemExit(f"Missing data file: data/{pattern}")
    return files[-1]


def load_local_waves():
    txt = latest("local_waves_*.txt").read_text()
    return [(d(m[0]), int(m[1])) for m in re.findall(r"^\s+(\d{4}-\d\d-\d\d)\s+(\d+) pkgs", txt, re.M)]


def load_branch_lag():
    txt = latest("branch_lag_*.txt").read_text()
    rows, weeks, section = [], {"arch": [], "stable": []}, None
    for line in txt.splitlines():
        if line.startswith("package "):
            section = "table"
            continue
        if line.startswith("Packages built per ISO week"):
            section = "weeks"
            continue
        if section == "table" and line.strip():
            cells = re.findall(r"(\S+ \(\d{4}-\d\d-\d\d\)|(?<!\S)-(?!\S))", line[17:])
            rows.append((line[:16].strip(), cells))
        elif section == "table":
            section = None
        elif section == "weeks":
            m = re.match(r"\s+(arch|stable):", line)
            if m:
                cur = m[1]
                continue
            m = re.match(r"\s+(\d{4}-W\d\d)\s+(\d+)", line)
            if m:
                weeks[cur].append((m[1], int(m[2])))
    return rows, weeks


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


def gap_chart(ann, today, W=700, H=132):
    """Bars at each stable update date; height = days since the previous update."""
    L, R, T, B = 34, 70, 14, 22
    start, end = date(2025, 1, 1), today + timedelta(days=10)
    span = (end - start).days
    x = lambda dt: L + (dt - start).days / span * (W - L - R)
    gaps = [(a["date"], (a["date"] - p["date"]).days, a["title"]) for p, a in zip(ann, ann[1:])]
    open_gap = (today - ann[-1]["date"]).days
    ymax = 80
    y = lambda v: H - B - v / ymax * (H - T - B)
    med = statistics.median(g for _, g, _ in gaps)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Days between Manjaro stable updates">',
           '<defs><pattern id="hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           f'<line x1="0" y1="0" x2="0" y2="4" stroke="{BLUE}" stroke-width="1.6"/></pattern></defs>']
    for v in (0, 40, 80):
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{GRID}" stroke-width="0.6"/>')
        out.append(text(L - 4, y(v) + 3, v, 8, MUTED, "end"))
    out.append(text(4, T - 4, "days", 8, MUTED))
    for yr_m in [date(2025, m, 1) for m in (1, 4, 7, 10)] + [date(2026, m, 1) for m in (1, 4, 7, 10)]:
        out.append(text(x(yr_m), H - 8, yr_m.strftime("%b %Y" if yr_m.month == 1 else "%b"), 8, MUTED, "middle"))
    bw = 5
    for dt, g, title in gaps:
        out.append(bar(x(dt) - bw / 2, y(0), bw, y(0) - y(g), BLUE, f"{dt}: {g} d since previous update — {title}"))
    # current open gap: hatched bar at today
    ox = x(today) - bw / 2
    out.append(bar(ox, y(0), bw, y(0) - y(open_gap), "url(#hatch)",
                   f"{today}: {open_gap} d since {ann[-1]['date']} and still open", f'stroke="{BLUE}" stroke-width="1"'))
    out.append(text(ox + bw + 4, y(open_gap) + 3, f"{open_gap} d, still open", 9, INK, weight=700))
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(med):.1f}" y2="{y(med):.1f}" stroke="{INK2}" stroke-width="1" stroke-dasharray="3 3"/>')
    out.append(text(W - R + 4, y(med) + 3, f"median {med:g} d", 8, INK2))
    longest = max(gaps, key=lambda t: t[1])
    out.append(text(x(longest[0]) + 5, y(longest[1]) + 3, f"{longest[1]} d (to {longest[0]:%d %b %Y})", 8, INK2))
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(0)}" y2="{y(0)}" stroke="{MUTED}" stroke-width="0.8"/>')
    out.append("</svg>")
    return "".join(out), gaps, open_gap, med


def week_chart(weeks, W=340, H=118):
    """Grouped bars per ISO week: Arch vs Manjaro stable, one shared axis (same unit)."""
    L, R, T, B = 34, 6, 10, 22
    labels = [w for w, _ in weeks["arch"]]
    arch = dict(weeks["arch"])
    stab = dict(weeks["stable"])
    ymax = max(max(arch.values()), max(stab.values()))
    ymax = (ymax // 500 + 1) * 500
    y = lambda v: H - B - v / ymax * (H - T - B)
    slot = (W - L - R) / len(labels)
    bw = (slot - 8) / 2
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Packages built per week, Arch vs Manjaro stable">']
    for v in range(0, ymax + 1, 1000):
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{GRID}" stroke-width="0.6"/>')
        out.append(text(L - 4, y(v) + 3, v, 8, MUTED, "end"))
    for i, wk in enumerate(labels):
        x0 = L + i * slot + 3
        a, s = arch.get(wk, 0), stab.get(wk, 0)
        out.append(bar(x0, y(0), bw, y(0) - y(a), ORANGE, f"{wk} Arch: {a} packages"))
        out.append(bar(x0 + bw + 2, y(0), bw, y(0) - y(s), BLUE, f"{wk} Manjaro stable: {s} packages"))
        if s < 200:
            out.append(text(x0 + bw + 2 + bw / 2, y(s) - 3, s, 7, INK2, "middle"))
        out.append(text(x0 + slot / 2 - 3, H - 8, wk[-3:], 8, MUTED, "middle"))
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(0)}" y2="{y(0)}" stroke="{MUTED}" stroke-width="0.8"/>')
    out.append("</svg>")
    return "".join(out)


def local_chart(waves, today, W=340, H=118):
    """Packages upgraded on this laptop per update-wave day."""
    L, R, T, B = 34, 6, 10, 22
    start = date(waves[0][0].year, waves[0][0].month, 1)
    end = today + timedelta(days=5)
    span = (end - start).days
    x = lambda dt: L + (dt - start).days / span * (W - L - R)
    ymax = 1000
    y = lambda v: H - B - v / ymax * (H - T - B)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Packages upgraded per update wave on this laptop">']
    for v in (0, 500, 1000):
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{GRID}" stroke-width="0.6"/>')
        out.append(text(L - 4, y(v) + 3, v, 8, MUTED, "end"))
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
    head = "<tr><th>package</th><th>Arch</th><th>unstable</th><th>testing</th><th>stable</th></tr>"
    body = []
    for name, cells in rows:
        tds = []
        for c in cells:
            m = re.match(r"(\S+) \((\d{4}-\d\d-\d\d)\)", c)
            if not m:
                tds.append('<td class="na">–</td>')
                continue
            age = (today - d(m[2])).days
            ver = re.sub(r"^\d+:", "", m[1]).rsplit("-", 1)[0]
            cls = "old" if age > 30 else ""
            tds.append(f'<td class="{cls}"><b>{esc(ver)}</b> <span>{age} d</span></td>')
        body.append(f"<tr><td class='pk'>{esc(name)}</td>{''.join(tds)}</tr>")
    return f"<table class='lag'>{head}{''.join(body)}</table>"


def build(today):
    ann = load_announcements()
    waves = load_local_waves()
    lag_rows, weeks = load_branch_lag()
    upstream = load_upstream()
    gsvg, gaps, open_gap, med = gap_chart(ann, today)
    gaps_2026 = [g for dt, g, _ in gaps if dt.year == 2026]
    longer = sum(1 for _, g, _ in gaps if g >= open_gap)
    lag_rows = [r for r in lag_rows if r[0] in ("linux71", "linux72", "plasma-desktop", "mesa", "systemd", "firefox")]
    up_rows = "".join(f"<tr><td class='pk'>{esc(u['upstream'])}</td><td>{esc(u['rhythm'])}</td>"
                      f"<td class='nw'>{esc(u['last'])}</td><td class='nw'>{esc(u['next'])}</td></tr>" for u in upstream)

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
@media screen and (max-width: 820px) {{ .page {{ width:auto; height:auto; padding:16px; }} .row {{ flex-direction:column; }} }}
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
.card {{ background:var(--surface); }}
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
  <div class="tile alert"><div class="v">❄ FROZEN</div><div class="l">since 2026-09-07: GitLab → Forgejo move. No end date announced.</div></div>
  <div class="tile"><div class="v">{open_gap} d</div><div class="l">since the last stable update ({ann[-1]['date']:%Y-%m-%d})</div></div>
  <div class="tile"><div class="v">{statistics.median(gaps_2026):g} d</div><div class="l">median gap in 2026 ({len(gaps_2026)} gaps, range {min(gaps_2026)}–{max(gaps_2026)} d)</div></div>
  <div class="tile"><div class="v">{longer} of {len(gaps)}</div><div class="l">gaps since 2025-02 were as long or longer. Rare, not a record.</div></div>
</section>

<section>
  <h2>Days between stable updates <span>· one bar per forum announcement, height = days since the previous one</span></h2>
  <div class="legend"><span><i class="sw" style="background:var(--blue)"></i>closed gap</span><span><i class="sw hatch"></i>current gap (still open)</span><span>- - - median of all gaps since 2025-02</span></div>
  {gsvg}
</section>

<section class="row">
  <div>
    <h2>Arch moves, stable does not <span>· packages built per week</span></h2>
    <div class="legend"><span><i class="sw" style="background:var(--orange)"></i>Arch core+extra</span><span><i class="sw" style="background:var(--blue)"></i>Manjaro stable</span></div>
    {week_chart(weeks)}
    <div class="note">The counts include only versions still in the repo, so older weeks look smaller. W36 is the last full stable update.</div>
  </div>
  <div>
    <h2>Update waves on this laptop <span>· days with ≥ 200 upgrades</span></h2>
    <div class="legend"><span><i class="sw" style="background:var(--blue)"></i>packages upgraded that day (from <code>pacman.log</code>)</span></div>
    {local_chart(waves, today)}
    <div class="note">Waves come every 2–4 weeks. October 2026 has only 12 upgrades so far, mostly Firefox and security packages.</div>
  </div>
</section>

<section class="row">
  <div style="flex:1.15">
    <h2>Where the packages wait <span>· version, build age</span></h2>
    {lag_table(lag_rows, today)}
    <div class="note">Shaded = older than 30 days. Unstable ≈ Arch, testing ≈ 2–3 weeks behind, stable 6–7 weeks behind. Security fixes (Firefox, CA certificates) still reach stable without an announcement.</div>
  </div>
  <div>
    <h2>Upstream rhythm <span>· what drives the waves</span></h2>
    <table><tr><th>upstream</th><th>rhythm</th><th>last</th><th>next</th></tr>{up_rows}</table>
    <div class="note">The autumn wave (kernel 7.3, Plasma 6.8, GNOME 51, Mesa 26.3) is out. Manjaro stable has none of it yet.</div>
  </div>
</section>

<section class="row">
  <div>
    <h2>Verdict</h2>
    <ul>
      <li><b>Yes, stable has slowed down.</b> The usual rhythm is one update every ~2 weeks, in irregular waves.</li>
      <li>The cause is Manjaro, not Linux or Arch. Arch builds <i>more</i> packages than usual right now.</li>
      <li>Reasons given: the Forgejo move, a slow GitLab, and a maintainer with "super limited time".</li>
      <li>Expect a <b>large</b> next update: Plasma 6.8 (SDDM → plasma-login-manager), systemd 262, kernel 7.2/7.3.</li>
      <li><b>Action:</b> <code>linux71</code> is end of life since 7.1.13. Move to <code>linux72</code> or keep <code>linux618</code> (LTS).</li>
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
    <div class="note">The <code>state</code> date also changes for small security pushes. It is not proof of a full update.</div>
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
