#!/usr/bin/env python3
"""
gitlab-jobs-now.py
List running and queued (pending) CI jobs across all projects accessible to the current user (non-admin).

Progress options:
  --progress               Show per-project start/finish updates (stderr).
  --heartbeat-secs N       Periodic "still working..." (stderr), default 8, 0 disables.

Usage:
  python3 main.py \
    --base-url https://git.example.com \
    --token $GITLAB_TOKEN \
    --format table \
    --concurrency 8 \
    --progress
"""

import argparse
import csv
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import gitlab
except ImportError:
    print("This script requires 'python-gitlab'. Install it with: pip install python-gitlab", file=sys.stderr)
    sys.exit(1)

PRINT_LOCK = threading.Lock()

# ----------------------------- Utilities -----------------------------

def iso_to_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        if s.endswith('Z'):
            s = s.replace('Z', '+00:00')
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        except Exception:
            try:
                return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except Exception:
                return None

def human_td(dt: timedelta) -> str:
    if dt.total_seconds() < 0:
        dt = -dt
    seconds = int(dt.total_seconds())
    parts = []
    for unit, div in (('d', 86400), ('h', 3600), ('m', 60)):
        if seconds >= div:
            parts.append(f"{seconds // div}{unit}")
            seconds %= div
    parts.append(f"{seconds}s")
    return "".join(parts)

def safe_get(d: Dict[str, Any], *keys, default=None):
    cur = d
    for k in keys:
        if cur is None:
            return default
        cur = cur.get(k)
    return cur if cur is not None else default

def err(msg: str):
    with PRINT_LOCK:
        print(msg, file=sys.stderr, flush=True)

# ------------------------- GitLab helpers ----------------------------

def build_client(base_url: str, token: Optional[str], verbose: bool) -> gitlab.Gitlab:
    gl = gitlab.Gitlab(url=base_url, private_token=token)
    gl.auth()
    if verbose:
        me = gl.user
        err(f"Authenticated as: {me.username} ({me.name})")
    return gl

def iter_projects(gl: gitlab.Gitlab, include_archived: bool, limit: Optional[int], only_paths: Optional[set], verbose: bool):
    count = 0
    try:
        for proj in gl.projects.list(
            membership=True,
            archived=include_archived,
            iterator=True,
            per_page=100,
            order_by="last_activity_at",
            sort="desc",
        ):
            path = proj.path_with_namespace
            if only_paths and path not in only_paths:
                continue
            yield proj
            count += 1
            if limit and count >= limit:
                break
    except gitlab.GitlabListError as e:
        err(f"Error listing projects: {e}")
        raise

def fetch_jobs_for_project(
    proj,
    want_running: bool = True,
    want_pending: bool = True,
    backoff: float = 1.0,
    verbose: bool = False,
) -> Tuple[str, str, List[Dict[str, Any]]]:
    path = getattr(proj, "path_with_namespace", str(proj.id))
    web_url = getattr(proj, "web_url", None)
    jobs: List[Dict[str, Any]] = []

    def _list_with_scope(scope_value: str) -> List[Any]:
        attempts = 0
        while True:
            attempts += 1
            try:
                return proj.jobs.list(scope=scope_value, per_page=100, all=True)
            except gitlab.exceptions.GitlabHttpError as e:
                if e.response_code == 429 and attempts <= 3:
                    time.sleep(backoff * attempts)
                    continue
                raise

    try:
        if want_running:
            for j in _list_with_scope("running"):
                jobs.append(j)
        if want_pending:
            for j in _list_with_scope("pending"):
                jobs.append(j)
    except gitlab.exceptions.GitlabAuthenticationError:
        if verbose:
            err(f"[auth] No access to jobs for {path}")
        return str(proj.id), path, []
    except gitlab.exceptions.GitlabHttpError as e:
        if verbose:
            err(f"[{path}] HTTP error fetching jobs: {e} (code {e.response_code})")
        return str(proj.id), path, []

    normalized: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for j in jobs:
        jd = j._attrs if hasattr(j, "_attrs") else dict(j)
        status = jd.get("status")
        started_at = iso_to_dt(jd.get("started_at"))
        created_at = iso_to_dt(jd.get("created_at"))
        queued_duration = jd.get("queued_duration")
        if queued_duration is None and created_at and status == "pending":
            queued_duration = (now - created_at).total_seconds()
        since = None
        if started_at and status == "running":
            since = now - started_at

        user_name = safe_get(jd, "user", "name") or safe_get(jd, "user", "username")
        runner_desc = safe_get(jd, "runner", "description") or safe_get(jd, "runner", "id")
        pipeline = jd.get("pipeline") or {}
        pipe_id = pipeline.get("id")
        pipe_iid = pipeline.get("iid")

        normalized.append(
            {
                "project_id": str(proj.id),
                "project_path": path,
                "project_web_url": web_url,
                "job_id": jd.get("id"),
                "name": jd.get("name"),
                "stage": jd.get("stage"),
                "status": status,
                "ref": jd.get("ref"),
                "tag": jd.get("tag"),
                "created_at": created_at.isoformat() if created_at else None,
                "started_at": started_at.isoformat() if started_at else None,
                "since": human_td(since) if since else None,
                "queued_seconds": int(queued_duration) if queued_duration is not None else None,
                "queued_human": human_td(timedelta(seconds=int(queued_duration))) if queued_duration is not None else None,
                "pipeline_id": pipe_id,
                "pipeline_iid": pipe_iid,
                "user": user_name,
                "runner": runner_desc,
                "job_url": f"{web_url}/-/jobs/{jd.get('id')}" if web_url and jd.get("id") else None,
            }
        )

    status_order = {"running": 0, "pending": 1}
    normalized.sort(key=lambda x: (status_order.get(x["status"], 99), x.get("stage") or "", x.get("name") or ""))
    return str(proj.id), path, normalized

# --------------------------- Output ----------------------------------

def print_table(grouped: Dict[str, List[Dict[str, Any]]], base_url: str, username: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    projects_scanned = len(grouped)
    projects_with_jobs = sum(1 for jobs in grouped.values() if jobs)
    total_running = sum(1 for jobs in grouped.values() for j in jobs if j["status"] == "running")
    total_pending = sum(1 for jobs in grouped.values() for j in jobs if j["status"] == "pending")

    line = "=" * 72
    print(line)
    print(f"Running & Queued Jobs (as of {now})")
    print(f"Account: {username}    Host: {base_url}    Projects scanned: {projects_scanned}")
    print(line)

    if total_running == 0 and total_pending == 0:
        print("No running or pending jobs found across your accessible projects.")
        return

    for path in sorted(grouped.keys()):
        jobs = grouped[path]
        if not jobs:
            continue
        print()
        print(path)
        print("-" * len(path))

        running = [j for j in jobs if j["status"] == "running"]
        pending = [j for j in jobs if j["status"] == "pending"]

        def _print_group(title: str, rows: List[Dict[str, Any]]):
            print(f"{title} ({len(rows)})")
            for j in rows:
                id_str = f"#{j['job_id']:>7}" if isinstance(j["job_id"], int) else f"#{j['job_id']}"
                since_or_q = f"since: {j['since']}" if j["status"] == "running" else (f"queued: {j['queued_human']}" if j["queued_human"] else "")
                url = j["job_url"] or ""
                print(
                    f"  {id_str}  {j['name']:<18}  stage: {j['stage'] or '-':<10}  "
                    f"ref: {j['ref'] or '-':<20}  {since_or_q:<12}  URL: {url}"
                )

        if running:
            _print_group("RUNNING", running)
        if pending:
            _print_group("PENDING", pending)

    print("-" * 71)
    print(f"TOTALS: running={total_running}  pending={total_pending}  across {projects_with_jobs}/{projects_scanned} projects with active jobs")

def print_json(items: List[Dict[str, Any]]):
    import json
    print(json.dumps(items, indent=2, sort_keys=False, default=str))

def print_csv(items: List[Dict[str, Any]]):
    fieldnames = [
        "project_path","project_id","job_id","status","name","stage","ref","tag",
        "user","runner","pipeline_id","pipeline_iid",
        "created_at","started_at","queued_seconds","job_url"
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    for j in items:
        writer.writerow({k: j.get(k) for k in fieldnames})

# -------------------------- Progress/Heartbeat -----------------------

def start_heartbeat(total: int, counter, interval_secs: int):
    """
    Prints a periodic 'still working...' line to stderr until counter.done == total.
    Returns (thread, stop_event).
    """
    stop_event = threading.Event()

    def _beat():
        start = time.time()
        while not stop_event.wait(timeout=interval_secs if interval_secs > 0 else 1e9):
            done = counter["done"]
            elapsed = human_td(timedelta(seconds=int(time.time() - start)))
            err(f"[heartbeat] still working… {done}/{total} projects done (elapsed {elapsed})")

    t = threading.Thread(target=_beat, name="heartbeat", daemon=True)
    if interval_secs > 0:
        t.start()
    return t, stop_event

# ----------------------------- Main ----------------------------------

def main():
    parser = argparse.ArgumentParser(description="List running and queued GitLab CI jobs across accessible projects.")
    parser.add_argument("--base-url", required=False, default=os.environ.get("GITLAB_URL") or os.environ.get("CI_SERVER_URL"),
                        help="GitLab base URL, e.g. https://git.example.com (env: GITLAB_URL)")
    parser.add_argument("--token", required=False, default=os.environ.get("GITLAB_TOKEN"),
                        help="Personal Access Token with read_api scope (env: GITLAB_TOKEN)")
    parser.add_argument("--include-archived", action="store_true", help="Include archived projects (default: false)")
    parser.add_argument("--projects", default="", help="Space-separated list of path_with_namespace to restrict scan")
    parser.add_argument("--max-projects", type=int, default=None, help="Limit number of projects scanned")
    parser.add_argument("--format", choices=["table","json","csv"], default="table", help="Output format")
    parser.add_argument("--concurrency", type=int, default=8, help="Parallel project fetchers (default: 8)")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging to stderr")
    parser.add_argument("--progress", action="store_true", help="Show per-project progress (stderr)")
    parser.add_argument("--heartbeat-secs", type=int, default=8, help="Periodic 'still working...' to stderr (0 disables)")
    args = parser.parse_args()

    if not args.base_url:
        err("Error: --base-url or GITLAB_URL must be provided.")
        sys.exit(1)
    if not args.token:
        err("Error: --token or GITLAB_TOKEN must be provided.")
        sys.exit(1)

    try:
        gl = build_client(args.base_url, args.token, args.verbose)
    except Exception as e:
        err(f"Failed to authenticate to GitLab: {e}")
        sys.exit(1)

    username = getattr(gl.user, "username", "unknown")
    only_paths = set(args.projects.split()) if args.projects.strip() else None

    if args.verbose:
        err("Enumerating projects…")
    try:
        projects_list = list(iter_projects(gl, args.include_archived, args.max_projects, only_paths, args.verbose))
    except Exception:
        sys.exit(1)

    total = len(projects_list)
    if args.verbose or args.progress:
        err(f"Found {total} projects to scan (concurrency={max(1, args.concurrency)})")

    # index projects so we can show [i/N]
    indexed_projects = [(i + 1, p) for i, p in enumerate(projects_list)]

    # Progress counters & heartbeat
    counter = {"done": 0}
    hb_thread, hb_stop = start_heartbeat(total, counter, args.heartbeat_secs)

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    all_items: List[Dict[str, Any]] = []

    def worker(idx: int, proj):
        path = getattr(proj, "path_with_namespace", str(proj.id))
        if args.progress:
            err(f"[{idx}/{total}] scanning {path} …")
        proj_id, path, jobs = fetch_jobs_for_project(proj, True, True, 1.0, args.verbose)
        running = sum(1 for j in jobs if j["status"] == "running")
        pending = sum(1 for j in jobs if j["status"] == "pending")
        if args.progress:
            mark = "✓" if jobs or True else "-"
            err(f"[{idx}/{total}] {mark} {path}: running={running} pending={pending}")
        return proj_id, path, jobs

    try:
        with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
            future_map = {
                executor.submit(worker, idx, p): (idx, p)
                for idx, p in indexed_projects
            }
            for fut in as_completed(future_map):
                idx, p = future_map[fut]
                try:
                    proj_id, path, jobs = fut.result()
                except Exception as e:
                    if args.verbose or args.progress:
                        err(f"[{idx}/{total}] {getattr(p, 'path_with_namespace', p.id)} failed: {e}")
                    counter["done"] += 1
                    continue
                grouped[path] = jobs
                all_items.extend(jobs)
                counter["done"] += 1
    finally:
        hb_stop.set()
        # give the heartbeat thread a moment to exit cleanly
        if hb_thread.is_alive():
            hb_thread.join(timeout=1)

    # Output
    if args.format == "table":
        print_table(grouped, args.base_url, username)
    elif args.format == "json":
        print_json(all_items)
    else:
        print_csv(all_items)

if __name__ == "__main__":
    main()
