<!--
SPDX-FileCopyrightText: 2026 Marcel Petrick

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Changelog

All notable changes to tokenUsage2. Versions follow semantic versioning; the
archive schema version is noted whenever it changes, because an older build
refuses a newer archive.

## 0.3.1

### Added

- `scripts/profile_app.py` times every stage the dashboard runs against the
  real home directory — cold indexing, warm start, an idle rescan, a snapshot
  per period, rendering and the JSON export — first without instrumentation,
  then under cProfile. Baseline on 1.5 GB of logs (45k events): cold index
  4.1 s, warm start 207 ms, idle rescan 21 ms, snapshot 69–79 ms, render 1.9 ms.

## 0.3.0

Archive schema 3 — migrated in place on first start.

### Fixed

- Backend labels were decided once at ingest and stored, so a `[backends]`
  config change or a newly discovered launcher never relabelled history. The
  archive now stores only what the log says (`route`: whether Anthropic's API
  answered, the Codex `model_provider`, the OpenCode `providerID`), and labels
  are resolved when displaying, cached per model.

## 0.2.0

Archive schema 2 — schema-1 archives are migrated in place on first start.

### Fixed

- A copied Claude home (for example `~/.claude-backup`, which the `$HOME` scan
  finds) counted every message a second time, because message keys included
  the account. Keys are now `(message.id, requestId)` across all homes; the
  migration rewrites old keys and drops the duplicates.
- Duplicates are recorded per pair of homes. A home whose records are mostly
  counted elsewhere is treated as a copy, so its retained daily totals from
  `stats-cache.json` are skipped too. `--doctor` reports both.

## 0.1.2

### Fixed

- Helper processes were counted as running agent sessions: the same `codex`
  and `claude` binaries also run `codex app-server`, `codex mcp-server`,
  `claude mcp serve`, `login`, `doctor` and similar. The subcommand is now
  checked (skipping option values such as `-c key=value`).

## 0.1.1

### Fixed

- A request stamped exactly at a local midnight landed in the newest bucket
  instead of its own day, and in the wrong heatmap cell: the `+ 1e-9` nudge used
  for the bucket lookup vanishes in float precision at epoch magnitudes. Buckets
  are now found with `bisect_right`.

## 0.1.0

- First release: live btop-style dashboard for Claude Code, Codex CLI and
  OpenCode token usage across every auto-discovered local account, with daily,
  weekly and monthly views, a SQLite archive (schema 1), `--once`, `--json`,
  `--doctor` and `--demo`.
