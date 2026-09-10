<!--
SPDX-FileCopyrightText: 2026 Marcel Petrick

SPDX-License-Identifier: GPL-3.0-or-later
-->

# tokenUsage2 — plan

A live, read-only terminal dashboard (in the spirit of btop, abtop and
AgentWhileTrue) that shows how many tokens every local coding agent burns,
per tool, per account and per backend, as daily, weekly and monthly views.

## 1. What `../tokenUsage` does today (review)

`tokenUsage` is a one-shot report pipeline:

1. `run-token-overview.sh` downloads the third-party *Token Use* binary
   (latest release, checksum file from the same release), runs its
   `doctor`/`overview`, and times each stage.
2. `render-overview.py` turns Token Use's overview JSON into a static HTML bar
   chart per tool.
3. `render-yearly.py` queries Token Use's private `archive.db` (`calls` table)
   and renders a 12-month HTML/CSV/JSON report.
4. `render-linkedin.py` renders a poster from Claude's `stats-cache.json` and
   Codex's `state_5.sqlite` `threads.tokens_used`.

Findings that shape tokenUsage2:

| # | Finding | Consequence for tokenUsage2 |
|---|---------|-----------------------------|
| 1 | Only `~/.claude` and `~/.codex` are read; a second `CODEX_HOME` (a company account) is invisible. | Auto-discover every home: `$HOME` scan by content markers, `CLAUDE_CONFIG_DIR`/`CODEX_HOME` from the environment **and** from shell rc files, plus a config file. Nothing machine-specific is hardcoded. |
| 2 | Claude records routed to Ollama or proxies are counted as "Claude" without distinction. | Classify the backend per request: `requestId` `req_…` means the Anthropic API; model → host mapping is recovered from `ANTHROPIC_BASE_URL` launchers in shell rc files. |
| 3 | `render-yearly.py` depends on the internal schema of a third-party binary that is downloaded as "latest" (the checksum comes from the same release, so it detects corruption, not tampering). | Zero runtime dependencies; parse the tools' own files directly. |
| 4 | `render-linkedin.py` hardcodes `unavailable=(5, 6)` and the "May–June" wording — correct for the 2026 snapshot only. | Retained-but-unsplit history is detected from the data and drawn hatched. |
| 5 | `render-overview.py` crashes on an empty `by_tool` (`max()` of nothing) and divides by zero when every total is 0. | Every renderer is tested with empty data. |
| 6 | Codex usage is attributed to the month the *thread started*. | Attribute every request to its own timestamp. |
| 7 | Snapshot only: Claude deletes transcripts after its cleanup period, so history is lost between runs. | Keep an own SQLite archive that is appended incrementally; history survives transcript cleanup. |
| 8 | No tests, no CI. | pytest + coverage gate, ruff, GitHub Actions, one `localPipeline.sh` for local and CI. |

## 2. Data sources (verified on a real machine)

| Tool | Where | Record | Dedup rule |
|------|-------|--------|------------|
| Claude Code | `<home>/projects/**/*.jsonl` | `type=assistant`, `message.usage` | The same message is written once per content block and streaming copies carry `output_tokens: 0`: key `(message.id, requestId)`, keep the **largest** copy. |
| Claude Code | `<home>/stats-cache.json` | `dailyModelTokens` | Only for days before the first surviving transcript; split unknown → drawn hatched. |
| Claude Code | statusline snapshots (`*rate-limit*.json`, `$XDG_STATE_HOME/*/quota/claude.json`) | 5h / 7d `used_percentage` | Newest `updated_at` wins. |
| Codex CLI | `<home>/sessions/**/rollout-*.jsonl`, `archived_sessions/` | `event_msg/token_count` with `info` | Rate-limit refreshes repeat the same cumulative total: key `(thread, cumulative total)`, value `last_token_usage`. The newer `token_usage_record` stream is ignored — its cumulative totals do not line up with `token_count`, and `token_count` matches Codex's own `threads.tokens_used`. |
| Codex CLI | same events | `rate_limits.primary/secondary` | Per account, newest observation wins. |
| Codex CLI | `<home>/auth.json` | `id_token` JWT claims | e-mail + plan only; tokens are never stored or shown. |
| OpenCode | `$XDG_DATA_HOME/opencode/opencode.db` | `message.data.tokens` | message id. |

Token semantics are normalised to *fresh input / cache read / cache write /
output (reasoning is a subset of output)*. Codex's `input_tokens` includes the
cached part and is split accordingly.

## 3. Ideas — what the dashboard can show

Implemented in v0.1 (✓) and backlog (·):

- ✓ Header: clock, live burn rate (tokens/min over 5 min), today / week /
  month / all-time totals.
- ✓ Accounts panel: one row per discovered account — tool, label, identity
  (e-mail, redactable), plan, today/week/month, 24 h sparkline, last activity,
  **live quota bars** (5 h and weekly) with reset countdown.
- ✓ Timeline: stacked bars for the last N days / ISO weeks / months, coloured
  by account, tool, backend or model; a cursor selects a bucket and scrolls
  back through history.
- ✓ Breakdown of the selected bucket by model, project, backend or account:
  calls, fresh input, cache read, cache write, output, total, share bar.
- ✓ Live feed: the newest requests with model, project and token split;
  just-arrived rows are highlighted.
- ✓ Heatmap: hour-of-day × weekday over the last four weeks.
- ✓ Metrics: raw total (incl. cache), fresh (input+output), output only.
- ✓ Sources overlay / `--doctor`: discovered homes, how each was found, file
  and event counts, archive path, backend hints, quota freshness, and
  reconciliation against Codex `threads.tokens_used` and Claude `stats-cache`.
- ✓ `--once` (one frame to stdout), `--json` (machine-readable snapshot),
  `--demo` (synthetic data for screenshots and tests).
- · API-equivalent cost with an editable price table.
- · Cache efficiency trend (cache read share per day).
- · Threshold notifications (quota ≥ 90 %, unusual burn rate).
- · Per-session drill-down and CSV export of the current view.
- · Aider / Gemini CLI / other agents as further parsers.

## 4. Architecture

```
discover.py  → Account list + backend hints (env, $HOME scan, rc files, config.toml)
parsers.py   → pure line/row → Event functions per tool
store.py     → SQLite archive (files, events, quotas, accounts), upsert-with-max
ingest.py    → incremental tail of append-only JSONL, OpenCode watermark, backfill
aggregate.py → buckets (DST-safe local midnights), tallies, account summaries
render.py    → cell canvas → ANSI/plain frame, themes, panels, overlays
tui.py       → alternate screen, cbreak keys, resize, refresh loop
cli.py       → --once / --json / --doctor / --demo / TUI
```

Python 3.14, standard library only (`sqlite3`, `tomllib`, `zoneinfo`,
`termios`). Rendering is plain ANSI text like AgentWhileTrue, so frames are
testable as strings.

## 5. Delivery

1. Plan (this file).
2. Package skeleton, discovery, parsers, archive + ingestion, aggregation,
   renderer, TUI + CLI — one commit each, each with tests.
3. `localPipeline.sh` (ruff, format, pytest with a coverage gate, smoke run,
   wheel build) and a GitHub Actions workflow running the same script.
4. README with badges and a screenshot rendered from `--demo`.
