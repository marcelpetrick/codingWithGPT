# GitLab MR comment resolver

Give it a merge request URL; it resolves every open discussion thread on that
merge request.

```bash
export GITLAB_TOKEN="glpat-…"
python3 main.py https://gitlab.example.com/group/project/-/merge_requests/42
```

```text
Merge request : https://gitlab.example.com/group/project/-/merge_requests/42
Project       : group/project
Acting as     : @mpetrick
Threads       : 3 to resolve, 5 skipped

Resolve:
  • src/parser.py (@alice)
      can you rename this to `parse_header`?
  • src/parser.py (@bob)
      nit: missing trailing newline
  • tests/test_parser.py (@alice)
      please add a case for the empty input

Skipped:
  - 2 × already resolved
  - 2 × standalone comment (GitLab cannot resolve these)
  - 1 × system note (has no resolved state)
  (use --show-skipped to list them individually)

Resolve 3 thread(s)? [y/N] y
[1/3] ✓ src/parser.py (@alice)
[2/3] ✓ src/parser.py (@bob)
[3/3] ✓ tests/test_parser.py (@alice)

Resolved 3/3 thread(s) in 0.8s
```

## Read this before you trust the word "all"

GitLab shows three different things in a merge request that all look like
comments, and **only one of them has a resolved state at all**:

| What you see in the UI | What it is in the API | Can it be resolved? |
| --- | --- | --- |
| A comment on a line of the diff | a thread whose notes are `resolvable` | **yes** |
| A comment typed into the box at the bottom of the *Overview* tab | a discussion with `individual_note: true` | **no** |
| "added 3 commits", "assigned to @x" | a note with `system: true` | **no** |

There is no API — and no button in the web UI — that resolves the bottom two
kinds. They simply have no resolved/unresolved state.

So this tool resolves all *resolvable threads* and prints every other comment
under **Skipped** with the reason. If the summary says `2 × standalone comment`,
those two comments are still there and always will be; that is GitLab's data
model, not a limitation of this script.

## The token you need to create

1. In GitLab, go to **Settings → Access tokens**.
2. Create a token with **scope `api`**, and **set an expiry date**.
3. Export it, or put it in a file:

```bash
export GITLAB_TOKEN="glpat-…"
# or
printf '%s' 'glpat-…' > ~/.gitlab-token && chmod 600 ~/.gitlab-token
python3 main.py <url> --token-file ~/.gitlab-token
```

### Why `api` and not something narrower

`api` is the minimum that works. Resolving a thread is a write, and `read_api`
is read-only; GitLab does not offer a finer-grained write scope for merge
request threads. There is nothing smaller to ask for.

### How to keep the blast radius small anyway

Since the scope cannot be narrowed, narrow the *token* instead:

- **Use a Project Access Token** (*Project → Settings → Access tokens*) rather
  than a Personal Access Token. A personal token can reach everything your
  account can reach; a project token is confined to that one project.
  A Group Access Token is the middle ground if you run this across one group.
- **Role: Developer.** That is the lowest role that may resolve threads.
  Rule of thumb: if the *Resolve thread* button is clickable for you in the web
  UI, this token can do it too. With a lower role the API answers `403` and the
  script tells you so.
- **Set an expiry.** GitLab requires one for project tokens and allows one for
  personal tokens; use the shortest that is practical.

### There is deliberately no `--token` flag

A token passed as a command line argument lands in your shell history and is
visible to every local user in `ps`. The token is therefore only read from
`GITLAB_TOKEN` or `--token-file`. If the token file is readable by others, the
script warns and suggests `chmod 600`.

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Usage

Preview without changing anything — do this first:

```bash
.venv/bin/python main.py <merge-request-url> --dry-run --show-skipped
```

Resolve, without the interactive prompt (for scripts and CI):

```bash
.venv/bin/python main.py <merge-request-url> --yes
```

Undo a run:

```bash
.venv/bin/python main.py <merge-request-url> --unresolve --yes
```

Resolve only the threads a particular reviewer started:

```bash
.venv/bin/python main.py <merge-request-url> --author alice --author bob
```

### Options

| Option | Effect |
| --- | --- |
| `--base-url URL` | GitLab server URL. Only needed when the instance is served under a subpath (`https://host/gitlab`); defaults to `$GITLAB_URL`. See below. |
| `--token-file PATH` | Read the token from a file instead of `$GITLAB_TOKEN`. |
| `--dry-run` | Show what would change, write nothing. |
| `--yes` / `-y` | Skip the confirmation prompt. |
| `--unresolve` | Reopen resolved threads instead of resolving open ones. |
| `--author USERNAME` | Only threads started by this user. Repeatable. |
| `--exclude-author USERNAME` | Skip threads started by this user. Repeatable. |
| `--max N` | Change at most N threads. |
| `--json` | Machine-readable report on stdout (human text moves to stderr). |
| `--show-skipped` | List every skipped thread instead of a per-reason summary. |
| `--quiet` | Suppress the per-thread progress lines. |
| `--timeout SECONDS` | HTTP timeout, default 30. |
| `--ca-bundle PATH` | Verify TLS against an internal certificate authority. |
| `--no-verify-ssl` | Disable TLS verification. Insecure; prefer `--ca-bundle`. |

### The `--base-url` / `GITLAB_URL` parameter

Normally you do not need it: the server is taken from the merge request URL you
pass in, so `https://gitlab.example.com/g/p/-/merge_requests/42` is enough.

You need it when your GitLab is served under a **path prefix**, for example
`https://intranet.example.com/gitlab/`. In that URL, `gitlab` is
indistinguishable from a top-level group name, so tell the script where the
instance starts:

```bash
export GITLAB_URL=https://intranet.example.com/gitlab
.venv/bin/python main.py https://intranet.example.com/gitlab/g/p/-/merge_requests/42
```

Accepted URL shapes: the modern `/-/merge_requests/<n>` form, the pre-13.0
`/merge_requests/<n>` form, nested subgroups, non-default ports, and trailing
sub-pages such as `/diffs?view=inline#note_5`.

## How it works

1. **Parse the URL** into instance, project path and merge request IID.
2. **Authenticate** (`GET /user`) so a bad token fails immediately, with a clear
   message, before anything is written.
3. **List the threads** — `GET /projects/:id/merge_requests/:iid/discussions`,
   following pagination.
4. **Classify each thread.** A thread is resolvable if any of its notes is, and
   counts as already resolved only when *every* resolvable note is resolved —
   the same rule the web UI uses to decide whether a thread is still open.
5. **Show the plan and ask.** Nothing is written before you say yes.
6. **Resolve each thread** — `PUT …/discussions/:discussion_id` with
   `resolved=true`, one request per thread.

## Safety and robustness

Resolving threads changes a shared merge request and is visible to your
reviewers, so the tool is built to be hard to fire by accident:

- The default run **prints the plan and asks for confirmation**.
- If stdin is not a terminal and `--yes` was not given, it **refuses to write**
  rather than assuming consent. So a run from cron or CI cannot resolve threads
  unless somebody explicitly opted in.
- `--dry-run` never writes.
- `--unresolve` reverses a run you regret.

Beyond that:

- Transient failures (`429`, `5xx`) are retried with backoff.
- One thread failing does not abort the others; each failure is reported with
  its own reason, and `403` is spelled out as a scope/role problem.
- Each write is verified against the server's response, so a request that
  returned `200` but changed nothing is reported as *unchanged* rather than
  counted as a success.
- Threads that are already in the target state are skipped, so re-running is
  harmless.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Everything requested succeeded (including "nothing to do"). |
| `1` | Ran, but at least one thread failed or did not change. |
| `2` | Usage, configuration, authentication or lookup error; nothing was written. |
| `130` | You declined the prompt, or pressed Ctrl-C. |

## Tests

```bash
.venv/bin/python -m unittest discover -s tests
```

53 tests, no network access: the GitLab client is faked. They cover URL parsing
(including the subpath and legacy forms), thread classification, the selection
and filter rules, per-thread error isolation, token handling, and the CLI's
confirmation and exit-code behaviour.

## Author & licence

Marcel Petrick <mail@marcelpetrick.it> — GPLv3 or later, see `../LICENSE`.
