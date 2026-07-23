# Plan: “show running & queued CI jobs across all projects I can access (non-admin)”

## 1) Approach & constraints

* Use the **python-gitlab** SDK (not admin). Auth with a **Personal Access Token** that has `read_api` scope.
* Because you’re not admin, we **can’t** hit instance-wide job endpoints; we’ll **iterate projects you can access** and query jobs per project.
* “Jobs” = CI jobs created by pipelines; we care about **statuses `running` and `pending`** (queued).

The implementation keeps pagination, progress, and machine-readable output
behavior explicit so large scans remain observable.

## 2) Inputs & configuration

* `GITLAB_URL` (e.g. `https://git.example.com`)
* `GITLAB_TOKEN` (or `--token` CLI flag)
* Optional CLI flags:

  * `--include-archived` (default: false)
  * `--projects "path1 path2 …"` (limit to a subset)
  * `--max-projects N` (quick runs)
  * `--format table|json|csv` (default: table)
  * `--verbose`
  * `--concurrency N` (default: 8)

## 3) Project discovery (non-admin)

* `gl.projects.list(membership=True, archived=False, simple=True, iterator=True, per_page=100)`.
* If `--projects` is given, resolve those paths directly instead of enumerating
  every membership.
* Handle per-project 403s (some groups may still deny job reads).

## 4) Fetch jobs per project

For each project:

* Call `project.jobs.list(scope=['running','pending'], per_page=100, get_all=True)`.
* For each job, capture:

  * `id`, `name`, `stage`, `status`, `ref`, `tag`, `created_at`, `started_at`, `queued_duration`, `duration`, `user`, `runner`
  * `pipeline` (`id`, `iid`)
  * Build a **web URL** as: `{project.web_url}/-/jobs/{job.id}`

## 5) Performance & robustness

* Use a bounded **ThreadPool** (e.g. `concurrent.futures.ThreadPoolExecutor(max_workers=concurrency)`) to fetch projects in parallel.
* Respect pagination and transparently report HTTP errors.
* Let `python-gitlab` honor `429 Retry-After` responses and its bounded retry
  policy.

## 6) Output (human-readable first)

Default **table** grouped by project, then status:

```
=======================================================================
Running & Queued Jobs (now)
Account: <your-username>   Host: <GITLAB_URL>   Projects scanned: 57
=======================================================================

project-a/backend
-----------------
RUNNING (2)
  #128374  build-linux     stage: build   ref: main   since: 3m12s   URL: …
  #128375  unit-tests      stage: test    ref: main   since: 1m02s   URL: …
PENDING (1)
  #128376  e2e-tests       stage: test    ref: main   queued: 45s    URL: …

project-b/frontend
------------------
PENDING (3)
  #99218   build           stage: build   ref: feature/auth  queued: 2m04s  URL: …
  …
-----------------------------------------------------------------------
TOTALS: running=12  pending=31  across 19/57 projects with active jobs
```

Other formats:

* `--format json` returns a stable schema (easy to pipe to jq).
* `--format csv` is for spreadsheets (columns: project, job_id, status, …).

## 7) CLI shape

```
gitlab-jobs-now.py \
  --base-url https://git.example.com \
  [--token $GITLAB_TOKEN] \
  [--projects "group/proj1 group/proj2"] \
  [--include-archived] \
  [--format table|json|csv] \
  [--concurrency 8] \
  [--verbose]
```

## 8) Covered edge cases

* Some projects hidden or lacking job read rights → warn & continue.
* Empty result (no running/pending anywhere) → print a friendly “none found” with totals.
* Very old GitLab versions missing `queued_duration` → fall back to “created_at → now”.
* Archived projects excluded unless `--include-archived`.
* Large accounts: cap projects with `--max-projects` for quick checks.

## 9) Testing

* Unit tests cover combined scopes, project discovery, archive handling, API
  failures, and output totals.
* Run a smoke test on the target instance with `--projects` or
  `--max-projects`.
* Compare counts against the GitLab UI filters (Jobs → Running / Pending).

## 10) Nice-to-haves (later)

* `--since` window and `--runner <name>` filter.
* Colorized TTY output.
* Per-project totals and an overall “queue age p95”.
