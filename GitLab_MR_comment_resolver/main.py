#!/usr/bin/env python3
"""
Resolve (or unresolve) all open discussion threads on a GitLab merge request.

Point it at a merge request URL; it lists every thread, shows what it intends to
change, asks for confirmation, and then resolves the open ones.

Only *resolvable threads* can be resolved. GitLab has no resolved state for
standalone comments on the MR overview or for system notes ("added 3 commits"),
so those are reported as skipped rather than silently ignored. See README.md.

Usage:
  export GITLAB_TOKEN="<token with 'api' scope>"
  python3 main.py https://gitlab.example.com/group/project/-/merge_requests/42
  python3 main.py <url> --dry-run
  python3 main.py <url> --yes --author alice
  python3 main.py <url> --unresolve          # undo
"""

import argparse
import json
import os
import stat
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

try:
    import gitlab
except ImportError:  # pragma: no cover - exercised only without the dependency
    print(
        "This script requires 'python-gitlab'. Install it with: "
        "pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(2)

EXIT_OK = 0
EXIT_PARTIAL_FAILURE = 1
EXIT_USAGE = 2
EXIT_ABORTED = 130

SNIPPET_LENGTH = 72

# ----------------------------- Data model -----------------------------


class MergeRequestUrlError(ValueError):
    """Raised when a merge request URL cannot be understood."""


class Failure(Exception):
    """A fatal but expected condition, reported without a traceback."""

    def __init__(self, message: str, code: int = EXIT_USAGE) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class MergeRequestRef:
    """A merge request located on some GitLab instance."""

    base_url: str  # e.g. "https://gitlab.example.com" (may include a subpath)
    project_path: str  # e.g. "group/subgroup/project"
    mr_iid: int  # the per-project number shown in the UI
    web_url: str  # canonical URL, rebuilt from the parts above


@dataclass
class ThreadInfo:
    """One discussion thread, reduced to what this tool needs to decide on it."""

    discussion_id: str
    resolvable: bool
    resolved: bool
    individual_note: bool
    system: bool
    author: Optional[str]  # username of the thread starter
    file_path: Optional[str]  # diff file the thread hangs on, if any
    snippet: str  # first line of the first human note
    note_count: int

    def label(self) -> str:
        """Short human-readable identification for tables and logs."""
        where = self.file_path or "overview"
        who = f"@{self.author}" if self.author else "unknown"
        return f"{where} ({who})"


@dataclass
class ThreadOutcome:
    """What actually happened to one thread during the apply phase."""

    thread: ThreadInfo
    status: str  # "changed" | "failed" | "no-op"
    detail: str = ""


@dataclass
class Selection:
    """Threads to act on, plus every thread that was left alone and why."""

    selected: List[ThreadInfo] = field(default_factory=list)
    skipped: List[Tuple[ThreadInfo, str]] = field(default_factory=list)


# ----------------------------- URL parsing -----------------------------


def _path_segments(path: str) -> List[str]:
    return [segment for segment in path.split("/") if segment]


def _find_merge_request_marker(segments: Sequence[str]) -> int:
    """Index of the 'merge_requests' segment that is followed by an IID.

    Raises MergeRequestUrlError if there is none.
    """
    for index, segment in enumerate(segments):
        if segment != "merge_requests":
            continue
        if index + 1 < len(segments) and segments[index + 1].isdigit():
            return index
    raise MergeRequestUrlError(
        "URL does not look like a merge request: expected a "
        "'.../merge_requests/<number>' path"
    )


def parse_merge_request_url(
    url: str, base_url_hint: Optional[str] = None
) -> MergeRequestRef:
    """Split a merge request URL into instance, project path and IID.

    Handles the '/-/' separator introduced in GitLab 13.0 as well as the older
    flat form, and tolerates trailing sub-pages, query strings and fragments.

    `base_url_hint` is needed only when the instance is served under a subpath
    (https://host/gitlab/...), because a path prefix is otherwise
    indistinguishable from a top-level namespace.
    """
    parsed = urlsplit(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise MergeRequestUrlError(
            f"URL must start with http:// or https://, got: {url!r}"
        )
    if not parsed.netloc:
        raise MergeRequestUrlError(f"URL has no host: {url!r}")

    segments = _path_segments(parsed.path)
    marker = _find_merge_request_marker(segments)
    mr_iid = int(segments[marker + 1])

    project_segments = list(segments[:marker])
    # GitLab 13.0+ inserts a '-' separator between project path and resource.
    if project_segments and project_segments[-1] == "-":
        project_segments.pop()

    origin = f"{parsed.scheme}://{parsed.netloc}"
    base_url = origin

    if base_url_hint:
        hint = urlsplit(base_url_hint.strip())
        if hint.netloc and hint.netloc != parsed.netloc:
            # Refusing beats silently preferring one over the other: a stale
            # GITLAB_URL pointing at another instance is a real mistake.
            raise MergeRequestUrlError(
                f"base URL host {hint.netloc!r} does not match the merge "
                f"request host {parsed.netloc!r}; unset GITLAB_URL or pass a "
                f"matching --base-url"
            )
        prefix = _path_segments(hint.path)
        if prefix:
            if project_segments[: len(prefix)] != prefix:
                raise MergeRequestUrlError(
                    f"merge request URL does not start with the configured base "
                    f"path {'/'.join(prefix)!r}"
                )
            project_segments = project_segments[len(prefix) :]
            base_url = f"{origin}/{'/'.join(prefix)}"

    if not project_segments:
        raise MergeRequestUrlError(
            f"could not determine the project path from URL: {url!r}"
        )

    project_path = "/".join(project_segments)
    return MergeRequestRef(
        base_url=base_url,
        project_path=project_path,
        mr_iid=mr_iid,
        web_url=f"{base_url}/{project_path}/-/merge_requests/{mr_iid}",
    )


# ----------------------------- Classification -----------------------------


def _truncate(text: str, limit: int = SNIPPET_LENGTH) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"


def _note_file_path(note: Dict[str, Any]) -> Optional[str]:
    position = note.get("position") or {}
    if not isinstance(position, dict):
        return None
    return position.get("new_path") or position.get("old_path")


def classify_discussion(discussion: Dict[str, Any]) -> ThreadInfo:
    """Reduce a raw discussion payload to the facts needed to act on it.

    A thread is *resolvable* when at least one of its notes is; it counts as
    *resolved* only when every resolvable note is resolved, which is how the web
    UI decides whether to show the thread as open.
    """
    notes = discussion.get("notes") or []
    resolvable_notes = [note for note in notes if note.get("resolvable")]
    human_notes = [note for note in notes if not note.get("system")]

    first_human = human_notes[0] if human_notes else None
    author = None
    if first_human:
        author = (first_human.get("author") or {}).get("username")

    file_path = None
    for note in notes:
        file_path = _note_file_path(note)
        if file_path:
            break

    return ThreadInfo(
        discussion_id=str(discussion.get("id", "")),
        resolvable=bool(resolvable_notes),
        resolved=bool(resolvable_notes)
        and all(note.get("resolved") for note in resolvable_notes),
        individual_note=bool(discussion.get("individual_note")),
        system=bool(notes) and not human_notes,
        author=author,
        file_path=file_path,
        snippet=_truncate(str(first_human.get("body", ""))) if first_human else "",
        note_count=len(notes),
    )


def select_threads(
    threads: Iterable[ThreadInfo],
    target_resolved: bool,
    authors: Sequence[str] = (),
    exclude_authors: Sequence[str] = (),
    limit: Optional[int] = None,
) -> Selection:
    """Split threads into those to change and those to leave alone (with reasons).

    `target_resolved` is the state we want: True to resolve, False to unresolve.
    """
    wanted = {author.lower().lstrip("@") for author in authors}
    unwanted = {author.lower().lstrip("@") for author in exclude_authors}
    verb = "resolved" if target_resolved else "unresolved"

    selection = Selection()
    for thread in threads:
        if thread.system:
            selection.skipped.append((thread, "system note (has no resolved state)"))
            continue
        if not thread.resolvable:
            reason = (
                "standalone comment (GitLab cannot resolve these)"
                if thread.individual_note
                else "not resolvable"
            )
            selection.skipped.append((thread, reason))
            continue
        if thread.resolved == target_resolved:
            selection.skipped.append((thread, f"already {verb}"))
            continue

        author = (thread.author or "").lower()
        if wanted and author not in wanted:
            selection.skipped.append((thread, "excluded by --author"))
            continue
        if author and author in unwanted:
            selection.skipped.append((thread, "excluded by --exclude-author"))
            continue
        if limit is not None and len(selection.selected) >= limit:
            selection.skipped.append((thread, f"beyond --max {limit}"))
            continue

        selection.selected.append(thread)

    return selection


# ----------------------------- GitLab access -----------------------------


def read_token(token_file: Optional[str], warn) -> str:
    """Read the API token from a file or the GITLAB_TOKEN environment variable.

    There is deliberately no --token flag: a token on the command line ends up in
    shell history and in the process list, where any local user can read it.
    """
    if token_file:
        try:
            with open(token_file, "r", encoding="utf-8") as handle:
                token = handle.read().strip()
        except OSError as error:
            raise Failure(f"error: cannot read --token-file: {error}")
        if not token:
            raise Failure(f"error: --token-file {token_file!r} is empty")
        try:
            mode = os.stat(token_file).st_mode
            if mode & (stat.S_IRWXG | stat.S_IRWXO):
                warn(
                    f"token file {token_file!r} is readable by other users; "
                    f"consider: chmod 600 {token_file}"
                )
        except OSError:
            pass  # permission reporting is a courtesy, not a requirement
        return token

    token = os.environ.get("GITLAB_TOKEN", "").strip()
    if not token:
        raise Failure(
            "error: no API token. Set GITLAB_TOKEN or pass --token-file PATH.\n"
            "       The token needs the 'api' scope; see README.md."
        )
    return token


def build_client(ref: MergeRequestRef, token: str, args) -> "gitlab.Gitlab":
    """Create an authenticated client, failing fast with an actionable message."""
    ssl_verify: Any = True
    if args.ca_bundle:
        ssl_verify = args.ca_bundle
    elif args.no_verify_ssl:
        ssl_verify = False

    client = gitlab.Gitlab(
        url=ref.base_url,
        private_token=token,
        ssl_verify=ssl_verify,
        timeout=args.timeout,
        retry_transient_errors=True,  # back off on 429 and 5xx instead of failing
    )
    try:
        client.auth()
    except gitlab.exceptions.GitlabAuthenticationError:
        raise Failure(
            f"error: authentication failed against {ref.base_url}.\n"
            "       Check that the token is valid, unexpired, and has the "
            "'api' scope."
        )
    except gitlab.exceptions.GitlabError as error:
        raise Failure(f"error: cannot reach {ref.base_url}: {error}")
    return client


def fetch_merge_request(client: "gitlab.Gitlab", ref: MergeRequestRef):
    """Look up the merge request, translating API errors into plain guidance."""
    try:
        project = client.projects.get(ref.project_path)
    except gitlab.exceptions.GitlabGetError as error:
        if error.response_code == 404:
            raise Failure(
                f"error: project {ref.project_path!r} not found on {ref.base_url}.\n"
                "       Either it does not exist or the token cannot see it."
            )
        raise Failure(f"error: cannot read project {ref.project_path!r}: {error}")

    try:
        return project.mergerequests.get(ref.mr_iid)
    except gitlab.exceptions.GitlabGetError as error:
        if error.response_code == 404:
            raise Failure(
                f"error: merge request !{ref.mr_iid} not found in "
                f"{ref.project_path!r}."
            )
        raise Failure(f"error: cannot read merge request !{ref.mr_iid}: {error}")


def fetch_threads(merge_request) -> List[ThreadInfo]:
    """List every discussion on the merge request, following pagination."""
    try:
        # get_all follows pagination; a busy merge request exceeds one page.
        discussions = merge_request.discussions.list(get_all=True)
    except gitlab.exceptions.GitlabError as error:
        raise Failure(f"error: cannot list discussions: {error}")
    return [classify_discussion(_attributes(item)) for item in discussions]


def _attributes(item: Any) -> Dict[str, Any]:
    """Accept either a python-gitlab object or a plain dict."""
    if isinstance(item, dict):
        return item
    return dict(getattr(item, "attributes", {}) or {})


def _verify(response: Any, target_resolved: bool) -> Optional[bool]:
    """Check the write actually took effect. None when the answer is unknowable."""
    if not isinstance(response, dict):
        return None
    notes = response.get("notes")
    if not isinstance(notes, list):
        return None
    resolvable = [note for note in notes if isinstance(note, dict) and note.get("resolvable")]
    if not resolvable:
        return None
    return all(bool(note.get("resolved")) is target_resolved for note in resolvable)


def apply_resolution(
    merge_request,
    threads: Sequence[ThreadInfo],
    target_resolved: bool,
    report=lambda message: None,
) -> List[ThreadOutcome]:
    """Set the resolution state of each thread, isolating per-thread failures."""
    outcomes: List[ThreadOutcome] = []
    total = len(threads)

    for index, thread in enumerate(threads, start=1):
        try:
            response = merge_request.discussions.update(
                thread.discussion_id, {"resolved": target_resolved}
            )
        except gitlab.exceptions.GitlabUpdateError as error:
            detail = _explain_update_error(error)
            outcomes.append(ThreadOutcome(thread, "failed", detail))
            report(f"[{index}/{total}] ✗ {thread.label()}: {detail}")
            continue
        except gitlab.exceptions.GitlabError as error:
            outcomes.append(ThreadOutcome(thread, "failed", str(error)))
            report(f"[{index}/{total}] ✗ {thread.label()}: {error}")
            continue

        verified = _verify(response, target_resolved)
        if verified is False:
            detail = "server reported the thread unchanged"
            outcomes.append(ThreadOutcome(thread, "no-op", detail))
            report(f"[{index}/{total}] ? {thread.label()}: {detail}")
        else:
            outcomes.append(ThreadOutcome(thread, "changed"))
            report(f"[{index}/{total}] ✓ {thread.label()}")

    return outcomes


def _explain_update_error(error) -> str:
    """Turn the common HTTP failures into something a user can act on."""
    code = getattr(error, "response_code", None)
    if code == 403:
        return (
            "forbidden — the token needs the 'api' scope and at least the "
            "Developer role (or MR authorship) on this project"
        )
    if code == 404:
        return "thread not found — it may have been deleted meanwhile"
    return str(error)


# ----------------------------- Presentation -----------------------------


def render_plan(
    ref: MergeRequestRef,
    username: Optional[str],
    selection: Selection,
    target_resolved: bool,
    show_skipped: bool,
    out=None,
) -> None:
    # Resolved at call time, not as a default argument: a default would bind the
    # stream at import time and ignore any later redirection of sys.stdout.
    out = sys.stdout if out is None else out
    verb = "Resolve" if target_resolved else "Unresolve"
    print(f"Merge request : {ref.web_url}", file=out)
    print(f"Project       : {ref.project_path}", file=out)
    if username:
        print(f"Acting as     : @{username}", file=out)
    print(
        f"Threads       : {len(selection.selected)} to {verb.lower()}, "
        f"{len(selection.skipped)} skipped",
        file=out,
    )
    print(file=out)

    if selection.selected:
        print(f"{verb}:", file=out)
        for thread in selection.selected:
            print(f"  • {thread.label()}", file=out)
            if thread.snippet:
                print(f"      {thread.snippet}", file=out)
        print(file=out)

    if selection.skipped and show_skipped:
        print("Skipped:", file=out)
        for thread, reason in selection.skipped:
            print(f"  - {thread.label()}: {reason}", file=out)
        print(file=out)
    elif selection.skipped:
        summary: Dict[str, int] = {}
        for _, reason in selection.skipped:
            summary[reason] = summary.get(reason, 0) + 1
        print("Skipped:", file=out)
        for reason, count in sorted(summary.items(), key=lambda kv: -kv[1]):
            print(f"  - {count} × {reason}", file=out)
        print("  (use --show-skipped to list them individually)", file=out)
        print(file=out)


def render_json(
    ref: MergeRequestRef,
    selection: Selection,
    outcomes: Sequence[ThreadOutcome],
    target_resolved: bool,
    dry_run: bool,
    out=None,
) -> None:
    out = sys.stdout if out is None else out  # see render_plan
    payload = {
        "merge_request": {
            "url": ref.web_url,
            "project": ref.project_path,
            "iid": ref.mr_iid,
        },
        "action": "resolve" if target_resolved else "unresolve",
        "dry_run": dry_run,
        "selected": [
            {
                "discussion_id": thread.discussion_id,
                "author": thread.author,
                "file": thread.file_path,
                "snippet": thread.snippet,
            }
            for thread in selection.selected
        ],
        "skipped": [
            {
                "discussion_id": thread.discussion_id,
                "author": thread.author,
                "file": thread.file_path,
                "reason": reason,
            }
            for thread, reason in selection.skipped
        ],
        "outcomes": [
            {
                "discussion_id": outcome.thread.discussion_id,
                "status": outcome.status,
                "detail": outcome.detail,
            }
            for outcome in outcomes
        ],
    }
    json.dump(payload, out, indent=2)
    print(file=out)


def confirm(prompt: str) -> bool:
    """Ask for explicit consent. Anything other than y/yes means no."""
    try:
        answer = input(f"{prompt} [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return False
    return answer in ("y", "yes")


# ----------------------------- Entry point -----------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve all open discussion threads on a GitLab merge request."
        ),
        epilog=(
            "The API token is read from GITLAB_TOKEN or --token-file and needs "
            "the 'api' scope. See README.md for least-privilege setup."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "url",
        help="merge request URL, e.g. https://host/group/project/-/merge_requests/42",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("GITLAB_URL"),
        help=(
            "GitLab instance base URL; required only when the instance is served "
            "under a subpath (https://host/gitlab). Defaults to $GITLAB_URL."
        ),
    )
    parser.add_argument(
        "--token-file",
        help="read the API token from this file instead of $GITLAB_TOKEN",
    )

    action = parser.add_argument_group("action")
    action.add_argument(
        "--unresolve",
        action="store_true",
        help="reopen resolved threads instead of resolving open ones",
    )
    action.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would change and exit without writing",
    )
    action.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="skip the confirmation prompt (required when stdin is not a terminal)",
    )

    filters = parser.add_argument_group("filters")
    filters.add_argument(
        "--author",
        action="append",
        default=[],
        metavar="USERNAME",
        help="only threads started by this user (repeatable)",
    )
    filters.add_argument(
        "--exclude-author",
        action="append",
        default=[],
        metavar="USERNAME",
        help="skip threads started by this user (repeatable)",
    )
    filters.add_argument(
        "--max",
        type=int,
        default=None,
        metavar="N",
        help="change at most N threads",
    )

    output = parser.add_argument_group("output")
    output.add_argument(
        "--json", action="store_true", help="emit a machine-readable JSON report"
    )
    output.add_argument(
        "--show-skipped",
        action="store_true",
        help="list every skipped thread instead of a per-reason summary",
    )
    output.add_argument(
        "--quiet", action="store_true", help="suppress per-thread progress lines"
    )

    connection = parser.add_argument_group("connection")
    connection.add_argument(
        "--timeout", type=float, default=30.0, metavar="SECONDS", help="HTTP timeout"
    )
    connection.add_argument(
        "--ca-bundle",
        metavar="PATH",
        help="verify TLS against this CA bundle (for internal certificate authorities)",
    )
    connection.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="disable TLS verification entirely (insecure; prefer --ca-bundle)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the tool. Returns a process exit code; never raises for expected errors."""
    try:
        return _run(build_parser().parse_args(argv))
    except Failure as failure:
        print(str(failure), file=sys.stderr)
        return failure.code
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return EXIT_ABORTED


def _run(args) -> int:

    # JSON output must stay parseable, so all human chatter goes to stderr.
    log = sys.stderr if args.json else sys.stdout

    def warn(message: str) -> None:
        print(f"warning: {message}", file=sys.stderr)

    if args.max is not None and args.max < 1:
        print("error: --max must be at least 1", file=sys.stderr)
        return EXIT_USAGE
    if args.no_verify_ssl and args.ca_bundle:
        print("error: --no-verify-ssl and --ca-bundle are mutually exclusive",
              file=sys.stderr)
        return EXIT_USAGE
    if args.no_verify_ssl:
        warn("TLS verification is disabled; the connection is not authenticated")

    try:
        ref = parse_merge_request_url(args.url, args.base_url)
    except MergeRequestUrlError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_USAGE

    token = read_token(args.token_file, warn)
    client = build_client(ref, token, args)
    username = getattr(client.user, "username", None)

    merge_request = fetch_merge_request(client, ref)
    threads = fetch_threads(merge_request)

    target_resolved = not args.unresolve
    selection = select_threads(
        threads,
        target_resolved=target_resolved,
        authors=args.author,
        exclude_authors=args.exclude_author,
        limit=args.max,
    )

    render_plan(
        ref, username, selection, target_resolved, args.show_skipped, out=log
    )

    verb = "resolve" if target_resolved else "unresolve"
    if not selection.selected:
        print(f"Nothing to {verb}.", file=log)
        if args.json:
            render_json(ref, selection, [], target_resolved, args.dry_run)
        return EXIT_OK

    if args.dry_run:
        print(f"Dry run: no threads were {verb}d.", file=log)
        if args.json:
            render_json(ref, selection, [], target_resolved, dry_run=True)
        return EXIT_OK

    if not args.yes:
        if not sys.stdin.isatty():
            print(
                f"error: refusing to {verb} {len(selection.selected)} thread(s) "
                "without confirmation.\n"
                "       stdin is not a terminal — pass --yes to proceed, or "
                "--dry-run to preview.",
                file=sys.stderr,
            )
            return EXIT_USAGE
        if not confirm(f"{verb.capitalize()} {len(selection.selected)} thread(s)?"):
            print("Aborted.", file=log)
            return EXIT_ABORTED

    started = time.monotonic()
    report = (lambda message: None) if args.quiet else (
        lambda message: print(message, file=log)
    )
    outcomes = apply_resolution(
        merge_request, selection.selected, target_resolved, report
    )
    elapsed = time.monotonic() - started

    changed = sum(1 for outcome in outcomes if outcome.status == "changed")
    failed = sum(1 for outcome in outcomes if outcome.status == "failed")
    noop = sum(1 for outcome in outcomes if outcome.status == "no-op")

    print(file=log)
    print(
        f"{verb.capitalize()}d {changed}/{len(outcomes)} thread(s) in "
        f"{elapsed:.1f}s"
        + (f", {failed} failed" if failed else "")
        + (f", {noop} unchanged" if noop else ""),
        file=log,
    )
    print(f"See {ref.web_url}", file=log)

    if args.json:
        render_json(ref, selection, outcomes, target_resolved, dry_run=False)

    return EXIT_PARTIAL_FAILURE if (failed or noop) else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
