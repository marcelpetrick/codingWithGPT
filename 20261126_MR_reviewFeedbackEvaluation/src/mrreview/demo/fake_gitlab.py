# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""A fake GitLab REST v4 server over real HTTP, serving a Fixture.

It checks the token, paginates like GitLab, refuses every method except GET, and can
inject faults (status codes) to test retry and resumption.
"""

from __future__ import annotations

import difflib
import json
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from mrreview.demo.fixture import Fixture

_ROUTES = [
    (re.compile(r"^/api/v4/projects$"), "projects"),
    (re.compile(r"^/api/v4/merge_requests$"), "all_mrs"),
    (re.compile(r"^/api/v4/projects/(\d+)/repository/compare$"), "compare"),
    (re.compile(r"^/api/v4/projects/(\d+)/merge_requests$"), "mrs"),
    (re.compile(r"^/api/v4/projects/(\d+)/merge_requests/(\d+)/discussions$"), "discussions"),
    (re.compile(r"^/api/v4/projects/(\d+)/merge_requests/(\d+)/approvals$"), "approvals"),
    (re.compile(r"^/api/v4/projects/(\d+)/merge_requests/(\d+)/versions$"), "versions"),
    (re.compile(r"^/api/v4/projects/(\d+)/merge_requests/(\d+)/versions/(\d+)$"), "version"),
    (re.compile(r"^/api/v4/projects/(\d+)/merge_requests/(\d+)/commits$"), "commits"),
]


class FakeGitLab:
    """Serve a fixture. faults maps a path regex to a list of statuses served first."""

    def __init__(self, fixture: Fixture, token: str = "test-token") -> None:
        self.fixture = fixture
        self.token = token
        self.faults: dict[str, list[int]] = {}
        self.methods: list[str] = []
        self.paths: list[str] = []
        self.lock = threading.Lock()

    def _list(self, route: str, groups: tuple[str, ...], query: dict[str, list[str]]) -> Any:
        fx = self.fixture
        if route == "projects":
            items = fx.projects
            if query.get("archived") == ["false"]:
                items = [p for p in items if not p["archived"]]
            return items
        if route == "all_mrs":
            since = query.get("updated_after", [""])[0].replace("+00:00", "Z")
            author = query.get("author_username", [None])[0]
            reviewer = query.get("reviewer_username", [None])[0]
            return [
                m
                for ms in fx.mrs.values()
                for m in ms
                if m["updated_at"] >= since
                and (author is None or m["author"]["username"] == author)
                and (
                    reviewer is None or reviewer in {r["username"] for r in m.get("reviewers", [])}
                )
            ]
        pid = int(groups[0])
        if route == "compare":
            return self._compare(pid, query.get("from", [""])[0], query.get("to", [""])[0])
        if route == "mrs":
            if pid not in fx.mrs:
                return None
            items = fx.mrs[pid]
            after = query.get("updated_after", [None])[0]
            if after:
                items = [m for m in items if m["updated_at"] >= after.replace("+00:00", "Z")]
            return sorted(items, key=lambda m: m["updated_at"])
        key = (pid, int(groups[1]))
        table: dict[str, dict[tuple[int, int], Any]] = {
            "discussions": fx.discussions,
            "versions": fx.versions,
            "commits": fx.commits,
            "approvals": fx.approvals,
        }
        if route == "version":
            return fx.version_detail.get((*key, int(groups[2])))
        return table[route].get(key)

    def _snapshot(self, pid: int, sha: str) -> dict[str, list[str]] | None:
        for (p, _iid, _vid), detail in self.fixture.version_detail.items():
            if p == pid and detail["head_commit_sha"] == sha:
                return {
                    d["new_path"]: [ln[1:] for ln in d["diff"].splitlines()[1:]]
                    for d in detail["diffs"]
                }
        return None

    def _compare(self, pid: int, from_sha: str, to_sha: str) -> Any:
        old, new = self._snapshot(pid, from_sha), self._snapshot(pid, to_sha)
        if old is None or new is None:
            return None
        diffs = []
        for path in sorted(set(old) | set(new)):
            a, b = old.get(path, []), new.get(path, [])
            if a == b:
                continue
            lines = list(difflib.unified_diff(a, b, lineterm="", n=3))[2:]
            diffs.append({"old_path": path, "new_path": path, "diff": "\n".join(lines) + "\n"})
        return {"commits": [], "diffs": diffs}

    def handle(
        self, method: str, raw_path: str, headers: dict[str, str]
    ) -> tuple[int, dict[str, str], bytes]:
        with self.lock:
            self.methods.append(method)
            self.paths.append(raw_path)
        if method != "GET":
            return 405, {}, b'{"message":"read-only fake"}'
        if headers.get("private-token") != self.token:
            return 401, {}, b'{"message":"401 Unauthorized"}'
        parts = urlsplit(raw_path)
        with self.lock:
            for pattern, statuses in self.faults.items():
                if statuses and re.search(pattern, parts.path):
                    status = statuses.pop(0)
                    return status, {"retry-after": "0"}, b'{"message":"injected"}'
        query = parse_qs(parts.query)
        for regex_, route in _ROUTES:
            m = regex_.match(parts.path)
            if not m:
                continue
            data = self._list(route, m.groups(), query)
            if data is None:
                return 404, {}, b'{"message":"404 Not Found"}'
            if isinstance(data, dict):
                return 200, {"content-type": "application/json"}, json.dumps(data).encode()
            per_page = int(query.get("per_page", ["20"])[0])
            page = int(query.get("page", ["1"])[0])
            chunk = data[(page - 1) * per_page : page * per_page]
            more = page * per_page < len(data)
            hdrs = {
                "content-type": "application/json",
                "x-page": str(page),
                "x-next-page": str(page + 1) if more else "",
                "x-total": str(len(data)),
            }
            return 200, hdrs, json.dumps(chunk).encode()
        return 404, {}, b'{"message":"404 Not Found"}'


def _handler(fake: FakeGitLab) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _serve(self) -> None:
            hdrs = {k.lower(): v for k, v in self.headers.items()}
            status, out_headers, body = fake.handle(self.command, self.path, hdrs)
            self.send_response(status)
            for k, v in out_headers.items():
                self.send_header(k, v)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = _serve
        do_POST = _serve
        do_PUT = _serve
        do_DELETE = _serve

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


@contextmanager
def serve(fake: FakeGitLab) -> Iterator[str]:
    """Run the fake on a free local port; yield its base URL."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(fake))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
