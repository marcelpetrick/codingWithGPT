<!--
SPDX-FileCopyrightText: 2026 Marcel Petrick

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Changelog

All notable changes to tokenUsage2. Versions follow semantic versioning; the
archive schema version is noted whenever it changes, because an older build
refuses a newer archive.

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
