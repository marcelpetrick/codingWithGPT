# Operations

## Commands

| Command | What it does |
|---|---|
| `mrreview collect` | Discover projects, collect MR history, build threads. |
| `mrreview evidence` | Ask the GitLab compare API whether the commented code changed later. |
| `mrreview analyze` | Classify substantive threads with the Ollama box. |
| `mrreview evaluate` | Decide outcomes, censoring and timings. |
| `mrreview report --out FILE` | Write the dashboard. Add `--demo` for synthetic data. |
| `mrreview run` | All stages in order. |
| `mrreview status` | Work state and coverage as JSON. |
| `mrreview smoke --authorized` | Bounded live run (2 projects, 5 MRs each, 20 threads). |
| `mrreview sample` / `agreement` | Manual quality check (see `docs/annotation_rubric.md`). |
| `mrreview db-pack` / `db-export` / `db-import` | Move the database between machines and tool versions. |

## Exit codes

| Code | Meaning | What to do |
|---|---|---|
| 0 | Done. | Nothing. |
| 1 | Error (configuration, unreachable server, bad file). The message names the cause. | Fix the cause, run the same command again. Work done so far is kept. |
| 2 | `smoke` refused: `--authorized` is missing. | Confirm the authorization of VISION.md section 8 first. |
| 3 | The time budget (`--max-minutes`) ran out and threads are still unclassified. | Run the same command again. |

## Scope widening (`scripts/widen.sh`)

1. Set `MRREVIEW_GITLAB_URL`, `MRREVIEW_GITLAB_TOKEN` (or `GITLAB_TOKEN`) and `MRREVIEW_FOCUS_USER`.
2. Start it detached: `systemd-inhibit --what=sleep:idle scripts/widen.sh > out/widen.stdout 2>&1 &`.
3. Watch `out/widen.log`. Open `out/real/dashboard.html`; it is rewritten after every chunk.
4. Stop after the current chunk: `touch out/widen.STOP`. Resume: remove the file and start the script again.

The script waits while another model is loaded on the Ollama box. After 6 failed checks (1 hour) it stops with exit code 4.

## Where the data is

| Path | Content | Delete with |
|---|---|---|
| `out/real/mrreview.sqlite3` (+ `-wal`, `-shm`) | Real review data, classifications, findings. Confidential. | `rm out/real/mrreview.sqlite3*` |
| `out/real/*.sqlite3.schema*-*.bak` | Backups made before a schema migration. | `rm` once the new version works. |
| `out/real/dashboard.html` | The report. Contains real names (behind the switch). Confidential. | `rm` |
| `out/demo/`, `out/live/` | Synthetic data only. | `rm -r` |

`out/` and `data/` are git-ignored. Never commit real data.

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| "GitLab unreachable, collection stopped" | Network or VPN. | Reconnect, run again. |
| "Ollama unreachable, analysis stopped" | The Ollama box is down or busy. | Check `curl http://<box>:11434/api/ps`, run again later. |
| "model … is not on the Ollama server" | Wrong `MRREVIEW_OLLAMA_MODEL`. | List models with `curl http://<box>:11434/api/tags`. |
| Dashboard says "Partial coverage" | Work is pending, a stage was not run, or the sample is bounded. | Hover the chip: it lists the reasons. |
| "database schema N is newer than this program" | The database comes from a newer mrreview. | Update mrreview, or import a `db-export` file. |
