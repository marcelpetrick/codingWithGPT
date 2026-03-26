## What

Create a **daily, UTC-aligned overview of a GitLab user’s activity stream** (events) for a given time window.
The script fetches all activities for a user (default: the authenticated user), buckets them into **1-day blocks (00:00–24:00 UTC)**, and prints the result to **stdout** in an LLM-friendly format or structured JSON.

This is designed as a **data extraction stage**: collect, normalize, and chunk activity data so it can be processed later (e.g. summarized by a Large Language Model).

No admin permissions are required; the script works entirely within the scope of the authenticated user.

---

## Virtual environment setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

---

## tl;dr

```bash
python3 main.py \
  --base-url https://git.data-modul.com \
  --token "$GITLAB_TOKEN" \
  --user mpetrick \
  --start 2026-01-01T00:00:00Z \
  --end 2026-12-31T23:59:59Z \
  --format llm-md --verbose > mpetrick_2026.txt
```

```bash
# Same call using numeric user ID (works for blocked users)
python3 main.py \
  --base-url https://git.data-modul.com \
  --token "$GITLAB_TOKEN" \
  --user-id 17 \
  --start 2026-01-01T00:00:00Z \
  --end 2026-12-31T23:59:59Z \
  --format llm-md --verbose > mpetrick_2026.txt
```

## Example call - in detail

Default behavior (current user, last 10 days, Markdown output):

```bash
python main.py --base-url https://git.example.com
```

Using username (default approach):

```bash
python main.py \
  --base-url https://git.example.com \
  --user mpetrick \
  --start 2026-01-01T00:00:00Z \
  --end   2026-01-11T00:00:00Z \
  --format llm-md
```

Using numeric user ID (e.g. for blocked or non-searchable users):

```bash
python main.py \
  --base-url https://git.example.com \
  --user-id 17 \
  --start 2026-01-01T00:00:00Z \
  --end   2026-01-11T00:00:00Z \
  --format llm-md
```

JSON output for downstream processing:

```bash
python main.py \
  --base-url https://git.example.com \
  --format json > activity.json
```

---

## Result

Example (excerpt, `--format llm-md`):

```text
# GitLab Activity Stream (Daily Buckets)

- User: mpetrick (Marcel Petrick)
- Host: https://git.example.com
- Window (UTC): 2026-01-01T00:00:00Z — 2026-01-11T00:00:00Z

## 2026-01-09 (UTC)
Window: 2026-01-09T00:00:00Z — 2026-01-10T00:00:00Z

- 09:14:32Z | MergeRequest | opened | group/project | Add caching to API | https://…
- 11:02:10Z | Issue        | commented | group/project | Flaky test on CI | https://…

Count: 2
```

Each day is emitted as a clearly delimited block, making it straightforward to feed into RAG (retrieval-augmented generation) or summarization pipelines.

![](example_output.png)

---

## Notes & tips

* **Auth**:
  Create a Personal Access Token with at least the `read_api` scope.
  Pass it via `--token` or the `GITLAB_TOKEN` environment variable (recommended).

* **User scope**:

  * Default: activity of the authenticated user.
  * Use `--user <username>` to fetch events for another user (must be visible to you).
  * Use `--user-id <id>` to fetch events by numeric user ID.

    This is particularly useful when:
    * the user is **blocked**
    * the user is **not returned by username search**
    * the instance restricts visibility of users

  * `--user` and `--user-id` are **mutually exclusive**.

* **Time window**:

  * Use `--start` / `--end` (ISO-8601, UTC recommended).
  * If omitted, the script defaults to **last 10 days ending now (UTC)**.
  * All bucketing is done strictly in **UTC**.

* **Output formats**:

  * `--format llm-md` (default): Markdown, optimized for LLM ingestion.
  * `--format json`: Stable structured schema for piping to tools like `jq` or custom post-processing.

* **Rate limits**:
  The script paginates through the GitLab Events API and stops early once events fall outside the requested window. A simple heartbeat option is included for slow instances.

* **Blocked users**:
  GitLab may not return blocked users via username lookup. In such cases, use `--user-id` to access their events directly.

* **Non-admin usage**:
  Works without admin rights; only accesses events visible to the authenticated user.

---

## Copyright
GPLv3; mail@marcelpetrick.it; zero warranty
