# Home filesystem audit — 2026-09-30

## Verdict

`/home` is an ext4 filesystem of about 807 GiB. Available space varied from 54 to 70 GiB during this audit; the latest measured value was about 67 GiB. A VirtualBox snapshot merge is in progress, so space may keep changing. The measured rebuildable cleanup set below is about 48 GiB and should put available space above 100 GiB from the latest reading. No files have been deleted.

## Plan and time budget

| Step | Estimate | State |
| --- | ---: | --- |
| Measure filesystem and top-level directories | 2 min | Done |
| Inspect large areas and classify safety | 5–10 min | Done |
| Calculate a conservative path to 100 GiB free | 3 min | Done |
| Report precise commands and cautions | 2 min | Done |

## Chronological status

| Time (UTC) | Status | Finding |
| --- | --- | --- |
| 18:57 | Measured | `/home`: 807G total, 700G used, 67G available. Home tree: 631G. |
| 18:57 | Measured | Largest directories: `VirtualBox VMs` 245G, `repos` 153G, `.local` 50G, `.cache` 20G, `Downloads` 20G. |
| 18:58 | Inspected | VirtualBox VM is in `deletingsnapshot` state. Leave all VM files alone until it finishes. |
| 19:00 | Inspected | Identified 48 GiB of npm download cache and ignored, generated project build files. Active npm process exists; wait for it to finish before clearing npm's cache. |
| 19:01 | Measured | Free space moved between 54 and 70 GiB during the audit; 67 GiB at latest check. No deletions. |

## Results

Sizes below are allocated bytes from `du -sxB1`, converted to GiB (2^30 bytes). These are estimates of potential recovery, not a promise of exact free-space change.

| Target | Allocated GiB | Classification and effect |
| --- | ---: | --- |
| `~/.npm/_cacache` | 11.09 | npm download cache; packages may need to be fetched again. An npm process was active during the audit, so wait until it ends. |
| `~/repos/DividendenDackel/.dart_tool/flutter_build` | 19.53 | Ignored Flutter build intermediates; rebuilt on next build. |
| `~/repos/DividendenDackel/build` | 6.58 | Ignored Flutter build outputs; rebuilt on next build. |
| `~/repos/CroLingo/build` | 3.29 | Ignored Android/Flutter build outputs; rebuilt on next build. |
| `~/repos/CroLingo/.tooling/cache` | 6.14 | Local tooling cache; may need to fetch/build again. |
| `~/repos/CroLingo/.tooling/trivy-cache` | 1.28 | Vulnerability scanner cache; definitions fetched again. |
| **Total** | **47.91** | No active processes for either Flutter project were found. Check again immediately before cleanup. |

Other recoverable areas, if more margin is needed:

- `~/.cache/uv/archive-v0` occupies 19.58 GiB. At least 8.81 GiB is in single-linked files; another 11.08 GiB has multiple hard links, so removing the cache might not reclaim the entire displayed size. uv would need to redownload/rebuild packages. Use `uv cache clean` only when uv jobs are idle.
- `~/.gradle/caches` is about 8.7 GiB; clear only when Gradle builds have stopped. Dependencies then need downloading again, so offline builds may fail.
- PyCharm Flatpak JetBrains cache is about 3.9 GiB; close PyCharm before clearing, and expect indexes to rebuild.
- Docker reports 40.39 GB of reclaimable images, but images may be useful to existing projects; inspect before any prune. Docker build cache reported 3.928 GB reclaimable.

Preserve without a specific owner decision:

- `~/VirtualBox VMs/P118 Kubuntu 22.04 Clone` uses about 245 GiB and is **currently deleting a snapshot**. Do not touch individual VDI/snapshot files. Review VM snapshots through VirtualBox after the merge finishes.
- `~/.local/share/myLastFmPlayer/downloads` (20G audio), `~/.local/share/germandubi/projects` (11G results), `~/sdk` (19G cross-compile SDK), Android emulator images/AVDs, `~/.ollama` models, and the 18G `jafed.ai/mvp/dist` deployment artifacts are data or installed components, not disposable caches.
- `~/repos/hr-doccontrol` has active work; do not clear its build artifacts now. A linked `easyanalyzer` worktree has uncommitted source changes; keep it.
- `~/Downloads/ubuntu-26.04-desktop-amd64.iso` is 6.1G, but keep or remove only after deciding it is no longer needed. The Trash is only about 104K.

The home directory uses about 638 GiB according to `du`, while `df` reports more used on the filesystem. `/home/docker` is root-owned and inaccessible without sudo. Docker's own report shows image/build-cache use; no Docker files were removed. The difference also includes filesystem overhead or other data not traversable by this user.

### Suggested cleanup sequence, when active builds are idle

Check VM and free space first:

```sh
VBoxManage showvminfo 'P118 Kubuntu 22.04 Clone' --machinereadable | rg '^VMState='
df -h /home
```

After confirming that no Flutter builds for these two projects and no npm install are running, remove only the measured caches/build outputs:

```sh
npm cache clean --force
rm -rf -- "$HOME/repos/DividendenDackel/.dart_tool/flutter_build" "$HOME/repos/DividendenDackel/build"
rm -rf -- "$HOME/repos/CroLingo/build" "$HOME/repos/CroLingo/.tooling/cache" "$HOME/repos/CroLingo/.tooling/trivy-cache"
df -h /home
```

The first Flutter build, scanner run, or package install afterward will take longer and may need network access. If free space remains below the target because the VM merge grows, wait for the merge to finish and remeasure before removing further items.

## Resume here

State: read-only audit complete; no deletion performed. A VirtualBox snapshot merge was still in progress at 19:01 UTC. The repository already had unrelated uncommitted work when this audit began; leave it alone.

Check commands:

```sh
df -hT /home/mpetrick
du -xhd1 /home/mpetrick 2>/dev/null | sort -h
VBoxManage showvminfo 'P118 Kubuntu 22.04 Clone' --machinereadable | rg '^VMState='
```

Restart commands: rerun the check commands, update the chronological status table, and use the suggested cleanup sequence only after active build/install processes have finished. Re-run `df -h /home` after each cleanup stage. Never unlink VDI or snapshot files directly.
