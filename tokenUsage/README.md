# Local token overview

`run-token-overview.sh` installs a checksum-verified, repo-local copy of
[Token Use](https://github.com/russmckendrick/tokenuse), scans the existing
Claude Code and Codex logs, and saves a self-contained `results/overview.html`,
machine-readable JSON, and wall-clock timings under `results/`.

```bash
./run-token-overview.sh 2026
```

The optional argument selects the calendar year; without it, the current year
is used. The yearly report includes paired monthly bar charts for Claude Code
and Codex, a cache-versus-fresh view, a fresh input/output view, and exact CSV
and JSON exports. When Chromium is available, it also renders a PNG snapshot.

When Claude's retained stats cache and Codex's thread database are available,
the same command also creates `linkedin-YEAR.html` and a 1200×1500 PNG. This
social version uses the retained application headline totals and marks monthly
history that can no longer be allocated precisely instead of displaying it as
zero.

The script does not need `sudo` and does not upload usage data. After it runs,
open the interactive chart dashboard with `.tools/tokenuse/tokenuse`; press
`1`–`5` to change the time range, `t` to switch tools, or `e` to export an
HTML, PDF, SVG, PNG, JSON, Excel, or CSV report.

Token Forest was the originally proposed graphical tool, but its official
builds support Windows and macOS only. Token Use is the Linux-compatible
replacement used here and reads the same `~/.claude/projects/**/*.jsonl` and
`~/.codex/sessions/**/rollout-*.jsonl` sources.
