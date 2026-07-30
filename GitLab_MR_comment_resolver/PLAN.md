# Plan: resolve all open threads on a GitLab merge request

## 1) Goal & scope

Given a merge request **URL**, resolve every open (unresolved) discussion thread on
that merge request, using the GitLab REST API via the **python-gitlab** SDK.

Non-goals: creating comments, approving, merging, or touching issues/commits.

## 2) The central API constraint

GitLab distinguishes three things that all look like "comments" in the web UI:

| Kind | API shape | Resolvable? |
| --- | --- | --- |
| Diff thread (comment on a code line) | discussion, `individual_note: false`, notes carry `resolvable: true` | **yes** |
| Standalone comment on the MR overview | discussion with `individual_note: true` | **no** |
| System note ("assigned to @x", "added 3 commits") | note with `system: true` | **no** |

There is **no API that resolves the non-resolvable kinds** — they have no resolved
state at all. So the tool must not claim to "resolve all comments"; it resolves all
*resolvable threads* and explicitly reports the rest as skipped, with a reason.
Silently doing nothing for those would be the main way this tool could mislead.

Endpoints used:

* `GET  /projects/:id/merge_requests/:iid/discussions` — list threads (paginated).
* `PUT  /projects/:id/merge_requests/:iid/discussions/:discussion_id` with
  `resolved=true|false` — set thread resolution.

In python-gitlab: `mr.discussions.list(get_all=True)` and
`mr.discussions.update(discussion_id, {"resolved": True})`.

Deliberately **not** `discussion.resolved = True; discussion.save()`: `SaveMixin`
builds its payload with `getattr(self, "resolved")`, and the discussion payload
returned by GitLab has no top-level `resolved` attribute, so that path raises
`AttributeError` on a stock response.

## 3) Credentials & least privilege

* **Scope `api`.** Resolving is a write; `read_api` is read-only and GitLab offers
  no narrower write scope for MR threads. This is the minimum that works.
* **Prefer a Project Access Token** over a Personal Access Token: it is bound to
  the single project, so the blast radius is one repository rather than everything
  the human account can reach.
* **Role: Developer** (or be the MR author). Rule of thumb: if the *Resolve thread*
  button is clickable in the web UI, the token can do it.
* **Set an expiry date.**
* Token is read from `GITLAB_TOKEN` or `--token-file`. There is intentionally **no
  `--token` flag** — an argv token leaks into shell history and `ps` output.

## 4) URL parsing

Accept the URLs people actually paste:

* `https://host/group/project/-/merge_requests/42`
* `https://host/group/sub/project/-/merge_requests/42/diffs#note_9`
* `https://host/group/project/merge_requests/42` (pre-13.0 style, no `/-/`)
* `https://host:8443/g/p/-/merge_requests/7?foo=bar`

Algorithm: split the path, find the `merge_requests` segment followed by digits,
everything before it (minus a trailing `-`) is the project path.

Ambiguity: on an instance served under a subpath (`https://host/gitlab/g/p/-/...`)
the path prefix is indistinguishable from a namespace. Resolved by requiring
`--base-url` / `GITLAB_URL` in that case, and stripping the prefix.

## 5) Safety model

Resolving threads is outward-facing — it changes a shared MR and is visible to
reviewers. So:

* Default run **prints the plan and asks for confirmation** (`y/N`).
* `--dry-run` prints the plan and exits without writing.
* `--yes` skips the prompt (for CI).
* Non-interactive stdin without `--yes` **aborts** rather than assuming consent.
* `--unresolve` performs the inverse, so an accidental run can be reverted.

## 6) Robustness

* `gl.auth()` up front to fail fast with a clear message and to report the acting user.
* `retry_transient_errors=True` so 429/5xx are retried with backoff.
* Per-thread error isolation: one failed thread does not abort the rest.
* Soft verification of each write: re-read the returned notes and warn on a
  silent no-op.
* Distinct exit codes: `0` ok, `1` partial failure, `2` usage/auth/config, `130` aborted.

## 7) Filters

`--author` / `--exclude-author` (repeatable, matched against the thread starter)
and `--max N`, so a reviewer can resolve only their own threads.

## 8) Deliverables

* `main.py` — the script; pure helpers (`parse_merge_request_url`,
  `classify_discussion`, `select_threads`) separated from I/O for testability.
* `tests/test_main.py` — unittest, no network, fake GitLab objects.
* `README.md` — token setup, usage, and the resolvable/non-resolvable caveat.
* `requirements.txt` — pinned.
