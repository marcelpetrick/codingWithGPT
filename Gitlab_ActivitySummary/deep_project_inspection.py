#!/usr/bin/env python3
"""
Deep GitLab project inspection for one user's visible contributions.

The script walks all projects visible to the token and records projects where
the target user appears in project events or commits. Project events include
comments, reviews, approvals, decisions, milestones, wiki activity, issues,
merge requests, and pushes on GitLab instances that expose those events.
Optional deep resource crawling can additionally inspect MR/issue notes and
discussions directly.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Set

try:
    import gitlab  # type: ignore
except ImportError:  # pragma: no cover
    print(
        "This script requires 'python-gitlab'. Install it with: pip install python-gitlab",
        file=sys.stderr,
    )
    raise


PRINT_LOCK = threading.Lock()
THREAD_LOCAL = threading.local()


def eprint(message: str) -> None:
    with PRINT_LOCK:
        print(message, file=sys.stderr, flush=True)


def die(message: str, code: int = 2) -> None:
    eprint(message)
    raise SystemExit(code)


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def fmt_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def human_td(delta: timedelta) -> str:
    seconds = int(abs(delta.total_seconds()))
    parts: List[str] = []
    for unit, div in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= div:
            parts.append(f"{seconds // div}{unit}")
            seconds %= div
    parts.append(f"{seconds}s")
    return "".join(parts)


def attrs(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    raw = getattr(obj, "_attrs", None)
    if isinstance(raw, dict):
        return raw
    return {}


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime

    def validate(self) -> None:
        if self.end <= self.start:
            raise ValueError("End must be after start.")

    def contains(self, value: Optional[str]) -> bool:
        dt = parse_iso8601(value)
        return bool(dt and self.start <= dt < self.end)


@dataclass(frozen=True)
class TargetUser:
    user_id: int
    username: str
    name: str
    emails: Set[str] = field(default_factory=set)

    def matches_author(self, author: Any) -> bool:
        data = attrs(author)
        if not data and not isinstance(author, dict):
            return False

        author_id = data.get("id")
        if author_id is not None and str(author_id) == str(self.user_id):
            return True

        username = str(data.get("username") or "").casefold()
        if username and username == self.username.casefold():
            return True

        name = str(data.get("name") or "").casefold()
        return bool(name and name == self.name.casefold())

    def matches_person_fields(self, data: Dict[str, Any], prefixes: Sequence[str]) -> bool:
        names = {self.username.casefold(), self.name.casefold()}
        emails = {mail.casefold() for mail in self.emails}

        for prefix in prefixes:
            raw_id = data.get(f"{prefix}_id")
            if raw_id is not None and str(raw_id) == str(self.user_id):
                return True

            raw_name = str(data.get(f"{prefix}_name") or "").casefold()
            if raw_name and raw_name in names:
                return True

            raw_email = str(data.get(f"{prefix}_email") or "").casefold()
            if raw_email and raw_email in emails:
                return True

        return False


@dataclass
class Evidence:
    kind: str
    action: str
    at: Optional[str]
    title: str
    url: str = ""


@dataclass
class ProjectResult:
    project_id: int
    path: str
    web_url: str
    first_activity: Optional[str] = None
    last_activity: Optional[str] = None
    evidence: List[Evidence] = field(default_factory=list)
    checked: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add(self, evidence: Evidence) -> None:
        key = (evidence.kind, evidence.action, evidence.at or "", evidence.title, evidence.url)
        for existing in self.evidence:
            existing_key = (existing.kind, existing.action, existing.at or "", existing.title, existing.url)
            if existing_key == key:
                return

        self.evidence.append(evidence)
        if evidence.at:
            if self.first_activity is None or evidence.at < self.first_activity:
                self.first_activity = evidence.at
            if self.last_activity is None or evidence.at > self.last_activity:
                self.last_activity = evidence.at

    def category_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in self.evidence:
            counts[item.kind] = counts.get(item.kind, 0) + 1
        return dict(sorted(counts.items()))


@dataclass(frozen=True)
class ProjectRef:
    project_id: int
    path: str
    web_url: str = ""


@dataclass(frozen=True)
class ScanConfig:
    base_url: str
    token: str
    target: TargetUser
    window: TimeWindow
    deep_resources: bool
    candidate_deep_only: bool
    all_commit_branches: bool
    skip_deep_resources: bool
    verbose: bool


def build_client(base_url: str, token: str, verbose: bool = False) -> "gitlab.Gitlab":
    gl = gitlab.Gitlab(url=base_url, private_token=token)
    gl.auth()
    if verbose:
        me = gl.user
        eprint(f"Authenticated as: {getattr(me, 'username', '?')} ({getattr(me, 'name', '?')})")
    return gl


def worker_client(config: ScanConfig) -> "gitlab.Gitlab":
    client = getattr(THREAD_LOCAL, "gitlab_client", None)
    if client is None:
        client = gitlab.Gitlab(url=config.base_url, private_token=config.token)
        THREAD_LOCAL.gitlab_client = client
    return client


def resolve_user(
    gl: "gitlab.Gitlab",
    username: Optional[str],
    user_id: Optional[int],
    extra_emails: Sequence[str],
    verbose: bool = False,
) -> TargetUser:
    if user_id is not None and username:
        die("Error: provide either --user or --user-id, not both.")

    if user_id is not None:
        user = gl.users.get(user_id)  # type: ignore[attr-defined]
    elif username:
        users = gl.users.list(username=username)  # type: ignore[attr-defined]
        if not users:
            die(f"User not found for --user '{username}'.")
        user = users[0]
    else:
        user = gl.user

    emails = {mail for mail in extra_emails if mail}
    for key in ("email", "public_email", "commit_email"):
        value = getattr(user, key, None)
        if value:
            emails.add(str(value))

    target = TargetUser(
        user_id=int(getattr(user, "id")),
        username=str(getattr(user, "username", username or "unknown")),
        name=str(getattr(user, "name", username or "unknown")),
        emails=emails,
    )
    if verbose:
        eprint(f"Resolved user: {target.username} (id={target.user_id})")
    return target


def start_heartbeat(interval_secs: int) -> threading.Event:
    stop = threading.Event()
    if interval_secs <= 0:
        return stop

    start_ts = time.time()

    def run() -> None:
        while not stop.wait(timeout=interval_secs):
            elapsed = human_td(timedelta(seconds=int(time.time() - start_ts)))
            eprint(f"[heartbeat] still working... elapsed {elapsed}")

    threading.Thread(target=run, name="heartbeat", daemon=True).start()
    return stop


def list_items(manager: Any, result: ProjectResult, label: str, **params: Any) -> Iterator[Any]:
    fallback_keys = {
        "updated_after",
        "updated_before",
        "created_after",
        "created_before",
        "since",
        "until",
        "all",
        "after",
    }
    try:
        yield from manager.list(iterator=True, per_page=100, **params)
    except (TypeError, gitlab.exceptions.GitlabError) as exc:
        cleaned = {k: v for k, v in params.items() if k not in fallback_keys}
        if cleaned == params:
            result.warnings.append(f"{label}: {exc}")
            return
        result.warnings.append(f"{label}: retrying without server-side filters after {exc}")
        try:
            yield from manager.list(iterator=True, per_page=100, **cleaned)
        except gitlab.exceptions.GitlabError as fallback_exc:  # pragma: no cover - depends on server permissions
            result.warnings.append(f"{label}: {fallback_exc}")
        except TypeError as fallback_exc:
            result.warnings.append(f"{label}: {fallback_exc}")
    except Exception as exc:  # pragma: no cover - depends on server permissions
        result.warnings.append(f"{label}: {exc}")


def project_path(project: Any) -> str:
    return str(
        getattr(project, "path_with_namespace", None)
        or getattr(project, "name_with_namespace", None)
        or getattr(project, "path", None)
        or getattr(project, "name", None)
        or getattr(project, "id", "unknown")
    )


def item_title(data: Dict[str, Any], fallback: str) -> str:
    for key in ("title", "target_title", "name", "path", "slug", "message"):
        value = data.get(key)
        if value:
            return str(value).replace("\n", " ")[:220]
    return fallback


def web_url(data: Dict[str, Any]) -> str:
    return str(data.get("web_url") or data.get("url") or data.get("target_url") or "")


def user_in_people(data: Dict[str, Any], keys: Sequence[str], target: TargetUser) -> bool:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            for item in value:
                if target.matches_author(item):
                    return True
        elif target.matches_author(value):
            return True
    return False


def inspect_project_events(project: Any, result: ProjectResult, target: TargetUser, window: TimeWindow) -> None:
    result.checked.append("project events")
    after = window.start.date().isoformat()
    for event in list_items(project.events, result, "project events", after=after):
        data = attrs(event)
        created = data.get("created_at")
        if not window.contains(created):
            continue
        if not target.matches_author(data.get("author")):
            continue
        result.add(
            Evidence(
                kind=str(data.get("target_type") or data.get("event_type") or "event"),
                action=str(data.get("action_name") or data.get("action") or "activity"),
                at=fmt_utc(parse_iso8601(created) or window.start),
                title=item_title(data, "project event"),
                url=web_url(data),
            )
        )


def inspect_commits(
    project: Any,
    result: ProjectResult,
    target: TargetUser,
    window: TimeWindow,
    all_commit_branches: bool = False,
) -> None:
    if not hasattr(project, "commits"):
        return
    result.checked.append("commits (all branches)" if all_commit_branches else "commits (default branch)")
    params: Dict[str, Any] = {"since": fmt_utc(window.start), "until": fmt_utc(window.end)}
    if all_commit_branches:
        params["all"] = True
    for commit in list_items(project.commits, result, "commits", **params):
        data = attrs(commit)
        committed_at = data.get("committed_date") or data.get("created_at") or data.get("authored_date")
        if not window.contains(committed_at):
            continue
        if not target.matches_person_fields(data, ("author", "committer")):
            continue
        result.add(
            Evidence(
                kind="commit",
                action="authored/committed",
                at=fmt_utc(parse_iso8601(committed_at) or window.start),
                title=item_title(data, str(data.get("short_id") or "commit")),
                url=web_url(data),
            )
        )


def inspect_notes(note_manager: Any, result: ProjectResult, target: TargetUser, window: TimeWindow, label: str, parent_title: str) -> None:
    for note in list_items(note_manager, result, f"{label} notes"):
        data = attrs(note)
        created = data.get("created_at") or data.get("updated_at")
        if not window.contains(created):
            continue
        if not target.matches_author(data.get("author")):
            continue
        result.add(
            Evidence(
                kind=f"{label} note",
                action="commented",
                at=fmt_utc(parse_iso8601(created) or window.start),
                title=parent_title,
                url=web_url(data),
            )
        )


def inspect_discussions(discussion_manager: Any, result: ProjectResult, target: TargetUser, window: TimeWindow, label: str, parent_title: str) -> None:
    for discussion in list_items(discussion_manager, result, f"{label} discussions"):
        data = attrs(discussion)
        notes = data.get("notes") if isinstance(data.get("notes"), list) else []
        for note in notes:
            created = note.get("created_at") or note.get("updated_at")
            if not window.contains(created):
                continue
            if not target.matches_author(note.get("author")):
                continue
            result.add(
                Evidence(
                    kind=f"{label} discussion",
                    action="review/commented",
                    at=fmt_utc(parse_iso8601(created) or window.start),
                    title=parent_title,
                    url=web_url(note),
                )
            )


def inspect_merge_requests(project: Any, result: ProjectResult, target: TargetUser, window: TimeWindow) -> None:
    if not hasattr(project, "mergerequests"):
        return
    result.checked.append("merge requests")
    params = {"state": "all", "updated_after": fmt_utc(window.start), "updated_before": fmt_utc(window.end)}
    for mr in list_items(project.mergerequests, result, "merge requests", **params):
        data = attrs(mr)
        title = item_title(data, f"MR !{data.get('iid', '?')}")

        created = data.get("created_at")
        updated = data.get("updated_at")
        if window.contains(created) and target.matches_author(data.get("author")):
            result.add(Evidence("merge request", "opened", fmt_utc(parse_iso8601(created) or window.start), title, web_url(data)))

        if window.contains(updated) and user_in_people(data, ("assignees", "reviewers"), target):
            result.add(Evidence("merge request", "assigned/reviewer", fmt_utc(parse_iso8601(updated) or window.start), title, web_url(data)))

        for action, key in (("merged", "merged_by"), ("merged", "merge_user"), ("closed", "closed_by")):
            if window.contains(updated) and target.matches_author(data.get(key)):
                result.add(Evidence("merge request", action, fmt_utc(parse_iso8601(updated) or window.start), title, web_url(data)))

        try:
            full_mr = project.mergerequests.get(data.get("iid"))
        except Exception:
            full_mr = mr

        if hasattr(full_mr, "notes"):
            inspect_notes(full_mr.notes, result, target, window, "merge request", title)
        if hasattr(full_mr, "discussions"):
            inspect_discussions(full_mr.discussions, result, target, window, "merge request", title)

        if hasattr(full_mr, "approvals"):
            try:
                approvals = attrs(full_mr.approvals.get())
                for approval in approvals.get("approved_by", []) or []:
                    user = approval.get("user") if isinstance(approval, dict) else None
                    if target.matches_author(user):
                        result.add(Evidence("merge request approval", "approved", fmt_utc(parse_iso8601(updated) or window.start), title, web_url(data)))
            except Exception as exc:  # pragma: no cover - depends on server edition/version
                result.warnings.append(f"merge request approvals: {exc}")


def inspect_issues(project: Any, result: ProjectResult, target: TargetUser, window: TimeWindow) -> None:
    if not hasattr(project, "issues"):
        return
    result.checked.append("issues")
    params = {"state": "all", "updated_after": fmt_utc(window.start), "updated_before": fmt_utc(window.end)}
    for issue in list_items(project.issues, result, "issues", **params):
        data = attrs(issue)
        title = item_title(data, f"issue #{data.get('iid', '?')}")
        created = data.get("created_at")
        updated = data.get("updated_at")

        if window.contains(created) and target.matches_author(data.get("author")):
            result.add(Evidence("issue", "opened", fmt_utc(parse_iso8601(created) or window.start), title, web_url(data)))

        if window.contains(updated) and user_in_people(data, ("assignees",), target):
            result.add(Evidence("issue", "assigned", fmt_utc(parse_iso8601(updated) or window.start), title, web_url(data)))

        if window.contains(updated) and target.matches_author(data.get("closed_by")):
            result.add(Evidence("issue", "closed", fmt_utc(parse_iso8601(updated) or window.start), title, web_url(data)))

        try:
            full_issue = project.issues.get(data.get("iid"))
        except Exception:
            full_issue = issue

        if hasattr(full_issue, "notes"):
            inspect_notes(full_issue.notes, result, target, window, "issue", title)
        if hasattr(full_issue, "discussions"):
            inspect_discussions(full_issue.discussions, result, target, window, "issue", title)


def inspect_milestones(project: Any, result: ProjectResult, target: TargetUser, window: TimeWindow) -> None:
    if not hasattr(project, "milestones"):
        return
    result.checked.append("milestones")
    for milestone in list_items(project.milestones, result, "milestones", state="all"):
        data = attrs(milestone)
        title = item_title(data, f"milestone {data.get('id', '?')}")
        created = data.get("created_at")
        updated = data.get("updated_at")
        if window.contains(created) and target.matches_author(data.get("author")):
            result.add(Evidence("milestone", "created", fmt_utc(parse_iso8601(created) or window.start), title, web_url(data)))
        if window.contains(updated) and target.matches_author(data.get("updated_by")):
            result.add(Evidence("milestone", "updated", fmt_utc(parse_iso8601(updated) or window.start), title, web_url(data)))


def inspect_wiki(project: Any, result: ProjectResult, target: TargetUser, window: TimeWindow) -> None:
    if not hasattr(project, "wikis"):
        return
    result.checked.append("wiki pages")
    for wiki in list_items(project.wikis, result, "wiki pages"):
        data = attrs(wiki)
        title = item_title(data, "wiki page")
        created = data.get("created_at")
        updated = data.get("updated_at")
        if window.contains(created) and target.matches_author(data.get("author")):
            result.add(Evidence("wiki page", "created", fmt_utc(parse_iso8601(created) or window.start), title, web_url(data)))
        if window.contains(updated) and target.matches_author(data.get("last_edited_by")):
            result.add(Evidence("wiki page", "updated", fmt_utc(parse_iso8601(updated) or window.start), title, web_url(data)))


def inspect_project(
    project: Any,
    target: TargetUser,
    window: TimeWindow,
    deep_resources: bool = False,
    candidate_deep_only: bool = False,
    all_commit_branches: bool = False,
    skip_deep_resources: bool = False,
    verbose: bool = False,
) -> ProjectResult:
    result = ProjectResult(
        project_id=int(getattr(project, "id")),
        path=project_path(project),
        web_url=str(getattr(project, "web_url", "")),
    )
    if verbose:
        eprint(f"Inspecting {result.path}")

    inspect_project_events(project, result, target, window)
    inspect_commits(project, result, target, window, all_commit_branches)

    if skip_deep_resources or not deep_resources or (candidate_deep_only and not result.evidence):
        result.evidence.sort(key=lambda item: (item.at or "", item.kind, item.title))
        return result

    inspect_merge_requests(project, result, target, window)
    inspect_issues(project, result, target, window)
    inspect_milestones(project, result, target, window)
    inspect_wiki(project, result, target, window)

    result.evidence.sort(key=lambda item: (item.at or "", item.kind, item.title))
    return result


def iter_projects(
    gl: "gitlab.Gitlab",
    exclude_archived: bool,
    membership_only: bool,
    max_projects: int,
    selected_projects: Sequence[str],
    verbose: bool = False,
) -> Iterator[Any]:
    if selected_projects:
        for project_ref in selected_projects:
            try:
                yield gl.projects.get(project_ref)  # type: ignore[attr-defined]
            except gitlab.exceptions.GitlabError as exc:
                matches = gl.projects.list(search=project_ref, iterator=True, per_page=100)  # type: ignore[attr-defined]
                yielded = False
                for match in matches:
                    match_path = project_path(match)
                    match_name = str(getattr(match, "name", "") or getattr(match, "path", ""))
                    if project_ref in {match_path, match_name, str(getattr(match, "id", ""))}:
                        yield gl.projects.get(getattr(match, "id"))  # type: ignore[attr-defined]
                        yielded = True
                if yielded:
                    continue
                if verbose:
                    eprint(f"Skipping project {project_ref}: {exc}")
        return

    params: Dict[str, Any] = {"iterator": True, "per_page": 100, "order_by": "id", "sort": "asc"}
    if exclude_archived:
        params["archived"] = False
    if membership_only:
        params["membership"] = True

    count = 0
    for project_ref in gl.projects.list(**params):  # type: ignore[attr-defined]
        if max_projects and count >= max_projects:
            break
        count += 1
        try:
            yield gl.projects.get(getattr(project_ref, "id"))  # type: ignore[attr-defined]
        except gitlab.exceptions.GitlabError as exc:
            if verbose:
                eprint(f"Skipping project {getattr(project_ref, 'id', '?')}: {exc}")


def enumerate_project_refs(
    gl: "gitlab.Gitlab",
    exclude_archived: bool,
    membership_only: bool,
    max_projects: int,
    selected_projects: Sequence[str],
    verbose: bool = False,
) -> List[ProjectRef]:
    refs: List[ProjectRef] = []
    for project in iter_projects(gl, exclude_archived, membership_only, max_projects, selected_projects, verbose):
        refs.append(
            ProjectRef(
                project_id=int(getattr(project, "id")),
                path=project_path(project),
                web_url=str(getattr(project, "web_url", "")),
            )
        )
    refs.sort(key=lambda item: (item.path.casefold(), item.project_id))
    return refs


def project_result_to_dict(item: ProjectResult) -> Dict[str, Any]:
    return {
        "project_id": item.project_id,
        "path": item.path,
        "web_url": item.web_url,
        "first_activity": item.first_activity,
        "last_activity": item.last_activity,
        "counts": item.category_counts(),
        "checked": item.checked,
        "warnings": item.warnings,
        "evidence": [e.__dict__ for e in item.evidence],
    }


def project_result_from_dict(data: Dict[str, Any]) -> ProjectResult:
    result = ProjectResult(
        project_id=int(data.get("project_id")),
        path=str(data.get("path") or data.get("project_id")),
        web_url=str(data.get("web_url") or ""),
        first_activity=data.get("first_activity"),
        last_activity=data.get("last_activity"),
        checked=list(data.get("checked") or []),
        warnings=list(data.get("warnings") or []),
    )
    for evidence in data.get("evidence") or []:
        if not isinstance(evidence, dict):
            continue
        result.evidence.append(
            Evidence(
                kind=str(evidence.get("kind") or ""),
                action=str(evidence.get("action") or ""),
                at=evidence.get("at"),
                title=str(evidence.get("title") or ""),
                url=str(evidence.get("url") or ""),
            )
        )
    return result


def scan_project_ref(project_ref: ProjectRef, config: ScanConfig) -> Dict[str, Any]:
    started = fmt_utc(datetime.now(timezone.utc))
    if config.verbose:
        eprint(f"[project:{project_ref.project_id}] start {project_ref.path}")

    try:
        gl = worker_client(config)
        project = gl.projects.get(project_ref.project_id)  # type: ignore[attr-defined]
        result = inspect_project(
            project,
            config.target,
            config.window,
            config.deep_resources,
            config.candidate_deep_only,
            config.all_commit_branches,
            config.skip_deep_resources,
            config.verbose,
        )
        record = {
            "type": "project",
            "status": "ok",
            "started_at": started,
            "finished_at": fmt_utc(datetime.now(timezone.utc)),
            "has_activity": bool(result.evidence),
            "project": project_result_to_dict(result),
        }
        if config.verbose:
            evidence_count = len(result.evidence)
            eprint(f"[project:{project_ref.project_id}] done {project_ref.path} evidence={evidence_count}")
        return record
    except Exception as exc:  # pragma: no cover - depends on server state
        if config.verbose:
            eprint(f"[project:{project_ref.project_id}] failed {project_ref.path}: {exc}")
        return {
            "type": "project",
            "status": "error",
            "started_at": started,
            "finished_at": fmt_utc(datetime.now(timezone.utc)),
            "has_activity": False,
            "project": {
                "project_id": project_ref.project_id,
                "path": project_ref.path,
                "web_url": project_ref.web_url,
            },
            "error": str(exc),
        }


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_completed_project_ids(path: Optional[str]) -> Set[int]:
    if not path:
        return set()
    output = Path(path)
    if not output.exists():
        return set()
    completed: Set[int] = set()
    with output.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") != "project":
                continue
            project = record.get("project") if isinstance(record.get("project"), dict) else {}
            project_id = project.get("project_id")
            if project_id is not None:
                completed.add(int(project_id))
    return completed


def render_json(meta: Dict[str, Any], results: List[ProjectResult]) -> None:
    payload = {
        "meta": meta,
        "projects": [project_result_to_dict(item) for item in results],
    }
    print(json.dumps(payload, indent=2, sort_keys=False))


def render_llm_md(meta: Dict[str, Any], results: List[ProjectResult], max_evidence_per_project: int = 0) -> None:
    print("# Deep GitLab Project Inspection")
    print()
    print(f"- User: {meta['user_username']} ({meta['user_name']})")
    print(f"- Host: {meta['base_url']}")
    print(f"- Window (UTC): {meta['start']} - {meta['end']}")
    print(f"- Visible projects inspected: {meta['projects_seen']}")
    print(f"- Projects with activity: {len(results)}")
    print(f"- Generated at (UTC): {meta['generated_at']}")
    print()
    print("| First activity (UTC) | Last activity (UTC) | Project/repository | Evidence counts |")
    print("| --- | --- | --- | --- |")
    for item in results:
        counts = ", ".join(f"{key}: {value}" for key, value in item.category_counts().items())
        print(f"| {item.first_activity or '-'} | {item.last_activity or '-'} | {item.path} | {counts} |")

    print()
    print("## Evidence")
    for item in results:
        print()
        print(f"### {item.path}")
        print(f"- First activity (UTC): {item.first_activity or '-'}")
        print(f"- Last activity (UTC): {item.last_activity or '-'}")
        if item.web_url:
            print(f"- URL: {item.web_url}")
        print(f"- Checked: {', '.join(item.checked)}")
        if item.warnings:
            print(f"- Warnings: {'; '.join(item.warnings)}")
        print()
        evidence_rows = item.evidence
        if max_evidence_per_project > 0:
            evidence_rows = item.evidence[:max_evidence_per_project]
        for evidence in evidence_rows:
            at = evidence.at or "-"
            url = f" | {evidence.url}" if evidence.url else ""
            print(f"- {at} | {evidence.kind} | {evidence.action} | {evidence.title}{url}")
        if max_evidence_per_project > 0 and len(item.evidence) > max_evidence_per_project:
            print(f"- ... {len(item.evidence) - max_evidence_per_project} additional evidence rows omitted in Markdown output")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect all visible GitLab projects for one user's contributions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--base-url", default=os.environ.get("GITLAB_URL") or os.environ.get("CI_SERVER_URL"))
    parser.add_argument("--token", default=os.environ.get("GITLAB_TOKEN"))
    parser.add_argument("--user", default=None, help="GitLab username, e.g. mpetrick")
    parser.add_argument("--user-id", type=int, default=None, help="GitLab user ID")
    parser.add_argument("--email", action="append", default=[], help="Additional commit email to match; can be repeated")
    parser.add_argument("--start", default="2020-01-01T00:00:00Z", help="Start time, ISO-8601")
    parser.add_argument("--end", default=None, help="End time, ISO-8601; defaults to now")
    parser.add_argument("--days", type=int, default=None, help="Optional lookback if --start is omitted")
    parser.add_argument("--format", choices=["llm-md", "json"], default="llm-md")
    parser.add_argument("--output", default=None, help="Append durable per-project JSONL records to this file")
    parser.add_argument("--resume", action="store_true", help="With --output, skip projects already recorded in the JSONL file")
    parser.add_argument("--workers", type=int, default=4, help="Parallel project inspections; 4 is a conservative default for GitLab")
    parser.add_argument("--project", action="append", default=[], help="Inspect only this project id or path; can be repeated")
    parser.add_argument("--exclude-archived", action="store_true", help="Skip archived projects")
    parser.add_argument("--deep-resources", action="store_true", help="Also crawl MR/issue notes, discussions, milestones, and wiki resources directly")
    parser.add_argument(
        "--membership-only",
        action="store_true",
        help="Only inspect projects where the authenticated token user is a direct member",
    )
    parser.add_argument(
        "--candidate-deep-only",
        action="store_true",
        help="Only run expensive MR/issue/wiki/milestone scans after project events or commits already show activity",
    )
    parser.add_argument(
        "--all-commit-branches",
        action="store_true",
        help="Inspect commits across all branches instead of only the default branch",
    )
    parser.add_argument(
        "--skip-deep-resources",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--max-evidence-per-project",
        type=int,
        default=0,
        help="Limit Markdown evidence rows per project; 0 means no limit",
    )
    parser.add_argument("--max-projects", type=int, default=0, help="Testing limit; 0 means no limit")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--heartbeat-secs", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if not args.base_url:
        die("Error: --base-url or GITLAB_URL/CI_SERVER_URL must be provided.")
    if not args.token:
        die("Error: --token or GITLAB_TOKEN must be provided.")

    end = parse_iso8601(args.end) if args.end else datetime.now(timezone.utc)
    if end is None:
        die(f"Invalid --end value: {args.end}")
    end = end.astimezone(timezone.utc).replace(microsecond=0)

    start = parse_iso8601(args.start) if args.start else None
    if start is None and args.days is not None:
        start = end - timedelta(days=max(1, int(args.days)))
    if start is None:
        die(f"Invalid --start value: {args.start}")
    start = start.astimezone(timezone.utc).replace(microsecond=0)

    window = TimeWindow(start=start, end=end)
    try:
        window.validate()
    except ValueError as exc:
        die(f"Invalid time window: {exc}")

    stop_hb = start_heartbeat(int(args.heartbeat_secs))
    try:
        gl = build_client(args.base_url, args.token, args.verbose)
        target = resolve_user(gl, args.user, args.user_id, args.email, args.verbose)

        project_refs = enumerate_project_refs(
            gl,
            bool(args.exclude_archived),
            bool(args.membership_only),
            int(args.max_projects),
            args.project,
            args.verbose,
        )

        completed = load_completed_project_ids(args.output) if args.resume else set()
        if completed and args.verbose:
            eprint(f"Resume enabled: skipping {len(completed)} projects already present in {args.output}")
        pending_refs = [ref for ref in project_refs if ref.project_id not in completed]

        workers = max(1, int(args.workers))
        if workers > 8 and args.verbose:
            eprint(f"Using {workers} workers; consider lowering this if the GitLab instance rate-limits requests.")

        meta = {
            "base_url": args.base_url,
            "user_id": target.user_id,
            "user_username": target.username,
            "user_name": target.name,
            "start": fmt_utc(window.start),
            "end": fmt_utc(window.end),
            "timezone": "UTC",
            "projects_seen": len(project_refs),
            "projects_pending": len(pending_refs),
            "selected_projects": args.project,
            "exclude_archived": bool(args.exclude_archived),
            "membership_only": bool(args.membership_only),
            "deep_resources": bool(args.deep_resources),
            "candidate_deep_only": bool(args.candidate_deep_only),
            "all_commit_branches": bool(args.all_commit_branches),
            "skip_deep_resources": bool(args.skip_deep_resources),
            "max_evidence_per_project": int(args.max_evidence_per_project),
            "workers": workers,
            "output": args.output,
            "resume": bool(args.resume),
            "generated_at": fmt_utc(datetime.now(timezone.utc)),
            "format": args.format,
        }

        if args.verbose:
            eprint(f"Enumerated {len(project_refs)} visible projects; scanning {len(pending_refs)} pending projects with {workers} workers.")

        output_path = Path(args.output) if args.output else None
        if output_path:
            append_jsonl(output_path, {"type": "meta", "meta": meta})

        config = ScanConfig(
            base_url=args.base_url,
            token=args.token,
            target=target,
            window=window,
            deep_resources=bool(args.deep_resources),
            candidate_deep_only=bool(args.candidate_deep_only),
            all_commit_branches=bool(args.all_commit_branches),
            skip_deep_resources=bool(args.skip_deep_resources),
            verbose=bool(args.verbose),
        )

        results: List[ProjectResult] = []
        ok_count = 0
        error_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(scan_project_ref, ref, config): ref for ref in pending_refs}
            for future in concurrent.futures.as_completed(futures):
                record = future.result()
                if output_path:
                    append_jsonl(output_path, record)
                if record.get("status") == "ok":
                    ok_count += 1
                    project_data = record.get("project") if isinstance(record.get("project"), dict) else {}
                    if record.get("has_activity"):
                        results.append(project_result_from_dict(project_data))
                else:
                    error_count += 1

        results.sort(key=lambda item: (item.first_activity or "9999", item.path.casefold()))
        summary = {
            "type": "summary",
            "finished_at": fmt_utc(datetime.now(timezone.utc)),
            "projects_seen": len(project_refs),
            "projects_scanned": len(pending_refs),
            "projects_ok": ok_count,
            "projects_error": error_count,
            "projects_with_activity": len(results),
        }
        if output_path:
            append_jsonl(output_path, summary)

        if args.format == "json":
            render_json({**meta, **summary}, results)
        else:
            render_llm_md({**meta, **summary}, results, int(args.max_evidence_per_project))
        return 0

    except gitlab.exceptions.GitlabAuthenticationError as exc:
        die(f"Authentication failed: {exc}", code=1)
    except gitlab.exceptions.GitlabHttpError as exc:
        die(f"GitLab HTTP error: {exc}", code=1)
    finally:
        stop_hb.set()


if __name__ == "__main__":
    raise SystemExit(main())
