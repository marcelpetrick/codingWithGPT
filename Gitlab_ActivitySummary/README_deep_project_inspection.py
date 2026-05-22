# Deep Project Inspection

`deep_project_inspection.py` checks every GitLab project visible to the supplied token and reports projects where the selected user appears to have contributed or made a decision. If the token can see every project in the GitLab instance, the script inspects the full instance-wide project set.

The call style matches `main.py`:

```bash
python3 deep_project_inspection.py \
  --base-url https://git.data-modul.com \
  --token "$GITLAB_TOKEN" \
  --user mpetrick \
  --start 2020-01-01T00:00:00Z \
  --end 2026-12-31T23:59:59Z \
  --output mpetrick_deep_project_inspection_2020_to_2026.jsonl \
  --format llm-md \
  --verbose > mpetrick_deep_project_inspection_2020_to_2026.md
```

The `--output` file is JSON Lines and is written after each project. If the run stops midway, keep that file and resume:

```bash
python3 deep_project_inspection.py \
  --base-url https://git.data-modul.com \
  --token "$GITLAB_TOKEN" \
  --user mpetrick \
  --start 2020-01-01T00:00:00Z \
  --end 2026-12-31T23:59:59Z \
  --output mpetrick_deep_project_inspection_2020_to_2026.jsonl \
  --resume \
  --format llm-md \
  --verbose > mpetrick_deep_project_inspection_2020_to_2026_resumed.md
```

Plain JSON summary to stdout:

```bash
python3 deep_project_inspection.py \
  --base-url https://git.data-modul.com \
  --token "$GITLAB_TOKEN" \
  --user mpetrick \
  --start 2020-01-01T00:00:00Z \
  --end 2026-12-31T23:59:59Z \
  --format json > mpetrick_deep_project_inspection_2020_to_2026.json
```

## What Gets Checked

The script walks all projects visible to the token, not only projects where the target user or token user is a member. By default it inspects these API surfaces when the GitLab server exposes them:

- project events, including pushes, comments, approvals, closed/opened items, wiki activity, joined projects, and milestone activity
- repository commits on the default branch where the user matches author or committer fields

With `--deep-resources`, it also crawls these resources directly:

- merge requests authored, assigned, reviewed, merged, closed, commented on, discussed, or approved by the user
- issues authored, assigned, closed, commented on, or discussed by the user
- milestones where author/update metadata is available
- wiki pages where author/update metadata is available

The output includes only projects with at least one evidence row.

## Matching Rules

User matching uses:

- GitLab user id
- GitLab username
- GitLab display name
- public or API-visible email fields
- extra commit emails passed with `--email`

Commit authorship is often only stored as name/email in Git, so pass additional known commit emails if needed:

```bash
python3 deep_project_inspection.py \
  --base-url https://git.data-modul.com \
  --token "$GITLAB_TOKEN" \
  --user mpetrick \
  --email marcel.petrick@example.com \
  --start 2020-01-01T00:00:00Z
```

## Useful Options

- `--user mpetrick`: resolve by username.
- `--user-id 17`: resolve by numeric GitLab user id.
- `--exclude-archived`: skip archived projects. By default, archived projects are included because the script checks all visible projects.
- `--membership-only`: narrow traversal to projects where the authenticated token user is a direct member. Do not use this for full instance inspection.
- `--deep-resources`: also crawl MR/issue notes, discussions, milestones, and wiki resources directly. This can be very slow across a full instance.
- `--candidate-deep-only`: with `--deep-resources`, only run expensive direct resource scans after project events or commits already show user activity.
- `--all-commit-branches`: inspect commits across all branches. This is slower; project push events are still checked without this option.
- `--max-evidence-per-project N`: limit Markdown evidence rows per project. Default `0` writes all evidence rows.
- `--output FILE.jsonl`: append one durable JSON record per project, plus run metadata and summary.
- `--resume`: with `--output`, skip projects already recorded in the JSONL file.
- `--workers N`: project-level parallelism. The default is `4`, which is conservative for a GitLab instance. Use `1` for easiest debugging; use higher values only if the server tolerates it.
- `--max-projects N`: limit project traversal for a smoke test.
- `--heartbeat-secs N`: print progress heartbeats to stderr during long runs.
- `--format llm-md`: Markdown report for reading or later summarization.
- `--format json`: structured output for `jq` or follow-up scripts.
- `--project P135-SW`: inspect only a specific project id or path. Can be repeated and is useful for focused validation.

## Notes

Use a token with `read_api` access. The script can only inspect projects and records visible to that token.

This inspection is much slower than `main.py` because it does not only fetch one user event stream. It first enumerates all visible projects, then inspects each project independently. Project records are flushed to `--output` immediately so partial runs remain usable and debugging can continue from the last completed project.

The default worker count is `4`. This is a cautious starting point for a private GitLab instance: enough to hide network latency, low enough to reduce the chance of rate limiting or overloading the API. If the server responds slowly or starts returning transient errors, rerun with `--workers 1` or `--workers 2`. If it is stable, `--workers 6` or `--workers 8` can be tried.

Some GitLab versions or permission scopes do not expose all metadata, for example milestone authors or approval timestamps. In those cases the script records warnings in the output and continues with the remaining checks.

-------
```sh
export GITLAB_TOKEN="..."

python3 deep_project_inspection.py \
  --base-url https://git.data-modul.com \
  --token "$GITLAB_TOKEN" \
  --user mpetrick \
  --start 2020-01-01T00:00:00Z \
  --end 2026-12-31T23:59:59Z \
  --workers 4 \
  --deep-resources \
  --output mpetrick_deep_project_inspection_2020_to_2026.jsonl \
  --format llm-md \
  --verbose \
  > mpetrick_deep_project_inspection_2020_to_2026.md

  If it stops or you interrupt it, resume with:

python3 deep_project_inspection.py \
  --base-url https://git.data-modul.com \
  --token "$GITLAB_TOKEN" \
  --user mpetrick \
  --start 2020-01-01T00:00:00Z \
  --end 2026-12-31T23:59:59Z \
  --workers 4 \
  --deep-resources \
  --output mpetrick_deep_project_inspection_2020_to_2026.jsonl \
  --resume \
  --format llm-md \
  --verbose \
  > mpetrick_deep_project_inspection_2020_to_2026_resumed.md
```
