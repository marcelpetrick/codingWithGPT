# PLAN.md — GitLab Activity Stream → Daily Chunks (LLM-compatible stdout)

## 1) Objective

Build a Python 3 CLI tool that:

1. Authenticates to GitLab using a **Personal Access Token** (PAT).
2. Fetches **activity stream events** for a target user (default: current authenticated user; optionally by `--user mpetrick`).
3. Restricts events to a requested time window:

   * If `--start` and/or `--end` are provided: use those.
   * Otherwise default to **last 10 days** (rolling window).
4. Buckets events into **1-day chunks** aligned to **UTC day boundaries** (00:00:00 → 23:59:59).
5. Prints to **stdout** in a stable, LLM-friendly schema so you can post-process later.

Non-goals:

* No LLM invocation inside the tool.
* No database; this is a fetch-and-print pipeline stage.

---

## 2) Inputs and Configuration

### Required

* `--base-url` (or env `GITLAB_URL` / `CI_SERVER_URL`)
* `--token` (or env `GITLAB_TOKEN`)

### Optional (time window)

* `--start <ISO8601>`: start time inclusive (e.g. `2026-01-01T00:00:00Z`)
* `--end <ISO8601>`: end time exclusive or inclusive (define and document; recommended: **exclusive** end for clean bucketing)
* Default: `end = now(UTC)`, `start = end - 10 days`

### Optional (user selection)

* `--user <username>` (default: authenticated user’s username)

  * Example: `--user mpetrick`
* `--user-id <int>` (optional override if username lookup is ambiguous; may be added as a robustness feature)

### Output format

* `--format llm-md|json` (default: `llm-md`)

  * `llm-md`: markdown blocks per day, with bullet items (easy ingestion)
  * `json`: structured list grouped by day (best for programmatic post-processing)

### Operational controls (carry over from existing style)

* `--verbose` (stderr logging)
* `--concurrency N` (optional; probably not needed unless we enrich events per project)
* `--progress` and `--heartbeat-secs N` (optional; likely not necessary_jobs-style not required, but keep pattern consistent)

---

## 3) Data Source: GitLab Activity Stream

### Approach

* Use `python-gitlab` for authentication and API calls.
* Fetch events from the **user activity endpoint** (GitLab exposes “events” per user).
* When `--user` is provided:

  * Resolve username → user object (ID), then fetch events for that user.
* When not provided:

  * Use `gl.user` (current user) and fetch its events.

### Pagination / Limits

* Use iterator-style listing or `page/per_page` loops.
* Stop fetching once events are older than `--start` (since results are typically reverse chronological).

### Filtering

* Server-side: if GitLab supports `after` / `before` params for events, use them.
* Client-side: always re-check event timestamps to enforce `[start, end)`.

---

## 4) Timestamp Handling and Day Bucketing

### Normalization

* Parse all times as timezone-aware.
* Convert everything to **UTC** internally.

### Bucket definition

* A day bucket is `[YYYY-MM-DDT00:00:00Z, YYYY-MM-DDT23:59:59Z]`
* Implementation should use half-open intervals for correctness:

  * bucket range: `[day_start, next_day_start)`
  * global range: `[start, end)` (recommended)

### Output ordering

* Days in ascending order (oldest → newest) to support incremental summarization.
* Events inside each day sorted by timestamp ascending (or keep original order; document choice).

---

## 5) Event Normalization (Stable Schema)

GitLab events vary by action type. Normalize each event into a consistent dict with:

* `event_id`
* `created_at` (ISO8601 UTC)
* `author` (username, name, id when available)
* `action_name` (or similar GitLab field)
* `target_type` (Issue/MergeRequest/PushEvent/etc.)
* `target_title` (best effort)
* `target_iid` / `target_id` (if present)
* `project`:

  * `path_with_namespace` (if available)
  * `web_url` (optional)
* `url` (best effort deep link; if not directly provided, construct if possible)
* `raw` (optional, behind `--include-raw`; otherwise omit to keep output compact)

This yields stable, LLM-friendly outputs regardless of event kind.

---

## 6) Output Design (stdout)

### Default: `--format llm-md`

Print one block per day:

* Header line with day and window:

  * `## 2026-01-09 (UTC)`
  * `Window: 2026-01-09T00:00:00Z — 2026-01-10T00:00:00Z`
* Then events as bullet lines with minimal but informative fields:

  * `- 14:32:10Z | MergeRequest | opened | group/proj | !123 Add caching | <url>`
  * `- 15:07:44Z | Issue | commented | group/proj | #456 Fix flaky test | <url>`

Include a short per-day summary footer:

* `Count: 17 events`

### Alternative: `--format json`

Emit a JSON object like:

```json
{
  "meta": { "user": "mpetrick", "start": "...", "end": "...", "timezone": "UTC" },
  "days": [
    {
      "date": "2026-01-09",
      "start": "...",
      "end": "...",
      "count": 17,
      "events": [ { ...normalized event... } ]
    }
  ]
}
```

---

## 7) Error Handling and Robustness

* Missing token / base-url → immediate error with actionable message.
* Authentication errors → fail fast.
* Username lookup failures → print clear error; suggest `--user-id`.
* Rate limiting (HTTP 429) → exponential backoff similar to existing code.
* Partial permissions (some events may reference projects you can’t read deeply) → still print the event; do not enrich further.

---

## 8) CLI Examples

### Default last 10 days for current user

```bash
python3 main.py --base-url https://git.example.com --token "$GITLAB_TOKEN"
```

### Explicit user + explicit window

```bash
python3 main.py \
  --base-url https://git.example.com \
  --token "$GITLAB_TOKEN" \
  --user mpetrick \
  --start 2026-01-01T00:00:00Z \
  --end   2026-01-11T00:00:00Z \
  --format llm-md
```

### JSON output for programmatic processing

```bash
python3 main.py --base-url ... --token ... --format json > activity.json
```

---

## 9) Implementation Steps

1. Refactor/replace `main.py` purpose: jobs → events.
2. Keep reusable utilities:

   * `iso_to_dt`, stderr logger, heartbeat/progress patterns (optional)
3. Implement:

   * `build_client()`
   * `resolve_user(gl, username)` → user object
   * `iter_events(gl, user_id, start, end)` with pagination and time cutoff
   * `bucket_events_by_day(events, start, end)` producing ordered day blocks
   * `render_llm_md(days)` and `render_json(days)`
4. Update README with new behavior and examples.
5. Ensure output is stable and free of ANSI or non-deterministic ordering.

---

## 10) Testing Plan

* Smoke test: run with default window, confirm non-empty output.
* Validate day bucketing: craft start/end that straddle midnight UTC.
* Compare a known day’s activity with GitLab UI “Activity” page.
* Test rate limiting handling (if possible) by reducing per_page and increasing calls.
* Verify that missing `--user` uses authenticated user.
