## What

Create an overview of currently running and planned jobs (for pipelines) for the Gitlab CI.  
Even when you don't have admin access - scan at least those projects you are part of.

## Example call
```
python main.py --base-url https://git.data-modul.com/  --format table --concurrency 1
```

### Notes & tips

* Auth: create a Personal Access Token with at least `read_api` scope; pass via `--token` or `GITLAB_TOKEN`.
* Non-admin scope: we enumerate only projects where you’re a member (`membership=True`) and query each project’s Jobs API.
* If your GitLab or `python-gitlab` version doesn’t expose `queued_duration`, the script computes a fallback “queued since” from `created_at`.
* Rate limits: basic backoff is included for 429s.
* Output:

  * `--format table` (default) prints a grouped, human-readable view.
  * `--format json` prints a stable schema for piping to `jq`.
  * `--format csv` is spreadsheet-friendly.

## Copyright
GPLv3; mail@marcelpetrick.it; zero warranty
