# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only GitLab REST v4 client (REQ-COL-1, REQ-SEC-1).

The client has no method that sends anything but GET.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator, Mapping
from typing import Any
from urllib.parse import quote, urlencode

from mrreview.http import HttpError, Response, Transport, request_with_retry

JSONDict = dict[str, Any]


class NotAccessible(RuntimeError):
    """The resource returned 403 or 404 (no access, deleted, or feature disabled)."""


class GitLabClient:
    """GET-only access to the GitLab REST API with offset pagination."""

    def __init__(
        self,
        base_url: str,
        token: str,
        transport: Transport,
        *,
        per_page: int = 100,
        timeout: float = 30.0,
        max_retries: int = 5,
        backoff_base: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api = base_url.rstrip("/") + "/api/v4"
        self._headers = {"PRIVATE-TOKEN": token, "Accept": "application/json"} if token else {
            "Accept": "application/json"
        }
        self._transport = transport
        self._per_page = per_page
        self._timeout = timeout
        self._retries = max_retries
        self._backoff = backoff_base
        self._sleep = sleep
        self.requests = 0

    def __repr__(self) -> str:
        return f"GitLabClient({self._api!r})"

    def _get(self, path: str, params: Mapping[str, object] | None = None) -> Response:
        url = self._api + path
        if params:
            url += "?" + urlencode({k: str(v) for k, v in params.items()})
        self.requests += 1
        try:
            return request_with_retry(
                self._transport, "GET", url, self._headers, timeout=self._timeout,
                max_retries=self._retries, backoff_base=self._backoff, sleep=self._sleep,
            )
        except HttpError as exc:
            if exc.status in (403, 404):
                raise NotAccessible(str(exc)) from None
            raise

    def get_json(self, path: str, params: Mapping[str, object] | None = None) -> Any:
        return json.loads(self._get(path, params).body or b"null")

    def paginate(self, path: str, params: Mapping[str, object] | None = None) -> Iterator[JSONDict]:
        """Yield every item of a list endpoint, page by page."""
        page = 1
        base = dict(params or {})
        while True:
            resp = self._get(path, {**base, "per_page": self._per_page, "page": page})
            items = json.loads(resp.body or b"[]")
            yield from items
            nxt = resp.headers.get("x-next-page", "")
            if nxt.strip():
                page = int(nxt)
            elif "x-next-page" in resp.headers or len(items) < self._per_page:
                return
            else:
                page += 1

    @staticmethod
    def _p(project_id: int) -> str:
        return quote(str(project_id), safe="")

    def projects(self, *, membership: bool, archived: bool) -> Iterator[JSONDict]:
        params: dict[str, object] = {"order_by": "id", "sort": "asc", "statistics": "false"}
        if membership:
            params["membership"] = "true"
        if not archived:
            params["archived"] = "false"
        return self.paginate("/projects", params)

    def merge_requests(self, project_id: int, updated_after: str | None = None) -> Iterator[JSONDict]:
        params: dict[str, object] = {"state": "all", "scope": "all", "order_by": "updated_at", "sort": "asc"}
        if updated_after:
            params["updated_after"] = updated_after
        return self.paginate(f"/projects/{self._p(project_id)}/merge_requests", params)

    def discussions(self, project_id: int, iid: int) -> Iterator[JSONDict]:
        return self.paginate(f"/projects/{self._p(project_id)}/merge_requests/{iid}/discussions")

    def approvals(self, project_id: int, iid: int) -> JSONDict:
        data = self.get_json(f"/projects/{self._p(project_id)}/merge_requests/{iid}/approvals")
        return data if isinstance(data, dict) else {}

    def versions(self, project_id: int, iid: int) -> Iterator[JSONDict]:
        return self.paginate(f"/projects/{self._p(project_id)}/merge_requests/{iid}/versions")

    def version(self, project_id: int, iid: int, version_id: int) -> JSONDict:
        data = self.get_json(
            f"/projects/{self._p(project_id)}/merge_requests/{iid}/versions/{version_id}"
        )
        return data if isinstance(data, dict) else {}

    def commits(self, project_id: int, iid: int) -> Iterator[JSONDict]:
        return self.paginate(f"/projects/{self._p(project_id)}/merge_requests/{iid}/commits")
