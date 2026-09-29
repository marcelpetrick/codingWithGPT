# What does the Ollama install script actually do?

Open `index.html` in a browser. It explains `curl -fsSL https://ollama.com/install.sh | sh` for engineers:
the `curl | sh` mechanics, the flow, every sudo call and why it needs root, what changes on disk, what is in the
1.4 GB download, quirks found in the code, and how to run it more carefully or undo it.

## Verdict so far

- Snapshot: release **v0.34.4**, fetched 2026-09-29, `install.sh` sha256 `25f64b81…2c9f`, 455 lines.
- On Linux the script installs to `/usr/local`, creates user and group `ollama`, and enables and restarts a systemd
  service. It installs GPU dependencies only for AMD (the ROCm bundle) and for NVIDIA without a driver
  (vendor repo + `cuda-drivers`, deb/rpm distros only).
- 39 script lines run through sudo. Every download runs unprivileged; only `tar` unpacks as root.
- The amd64 archive is 65 entries, 2.24 GB unpacked, 2.14 GB of it CUDA, all owned by `root:root`.
- Quirks 1, 2, 3 and 5 on the page reproduce with `verify_quirks.sh` (sh and bash). The installer itself was not run.

## Files

| File | What |
|---|---|
| `install.sh` | Pinned copy of the script the page describes |
| `ollama-linux-amd64.contents.txt` | `tar -tv` of the amd64 archive (streamed, never written to disk) |
| `FETCHED` | Fetch date and release tag |
| `page.template.html` | Hand-written prose with `{{PLACEHOLDERS}}` |
| `build.py` | Renders `index.html` (hash, line count, sudo-highlighted listing, archive table) |
| `refresh.sh` | Re-fetches the script and listing, then rebuilds |
| `verify_quirks.sh` | Reproduces the quirks without root |

## Status

| When (UTC) | Step | Result |
|---|---|---|
| 2026-09-29 11:17 | Fetched `install.sh` (redirects to a GitHub release asset) | 455 lines |
| 2026-09-29 11:19 | Streamed the amd64 archive through `tar -tv` | 65 entries |
| 2026-09-29 11:23 | Wrote the page and generator | commits `072f53a`, `80bdff5` |
| 2026-09-29 11:27 | Reproduced quirks 1/2/3/5 | all pass |

## Open

- No visual check yet: headless Chromium can't start in the agent sandbox (socket creation is blocked). Open
  `index.html` once in light and dark mode, desktop and phone width.

## Resume here

```sh
cd whatDoesTheOllamaInstallScriptActuallyDo
sh verify_quirks.sh          # quirks still reproduce
python3 build.py             # rebuild after editing page.template.html
./refresh.sh                 # newer script: re-fetch (streams ~1.4 GB), rebuild, then re-read the diff
git diff install.sh          # the prose must be re-checked against every changed line
```

If `install.sh` changed, the line numbers (`L123`) in `page.template.html` are stale. Re-check each section
against the diff before committing.
