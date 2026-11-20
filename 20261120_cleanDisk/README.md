# 20261120_cleanDisk: free disk space in `~/repos`

**Result:** about 30 GB free again on `/home`. Free space went from about 19 GB to 49 GB (94% used).
Seven repos went from 42.9 GB to 13.2 GB. No commit and no tracked file was lost.

## 1. Find the large repos

This command finds all git directories down to depth 3, then shows the ones over 1 GB, sorted by size:

```sh
cd ~/repos && find . -maxdepth 3 -name .git -prune -printf '%h\n' 2>/dev/null \
  | while read d; do du -sb "$d" 2>/dev/null; done \
  | awk '$1>1073741824' | sort -rn \
  | awk '{printf "%.2f GB\t%s\n",$1/1073741824,$2}'
```

The size counts the full directory: the working tree, `.git`, and ignored or untracked files.
A repo inside another repo is also counted in the size of its parent.

## 2. Check each target before the delete

Do these checks for each repo before `reset` and `clean`:

1. Show the modified tracked files: `git status --short --untracked-files=no`.
2. Show the unpushed commits: `git log --oneline @{u}..`.
3. Show the untracked files that are not ignored: `git status --short | grep '^??'`.
4. Show what `clean` removes, by size: `git clean -xfdn`, then `du -s` on each path.
5. Show the worktrees: `git worktree list`.

What the checks found:

- `Raumfreund`: 8 modified files (90 lines of real work, from 2026-11-08). They were kept in a stash (see step 3).
- `docker_experiments`: 15 "modified" files, but only file mode changes (0 insertions, 0 deletions). It was safe to reset.
- `tb-app`: this is a git worktree of `ThoraxGPT_from_Wish` (detached HEAD), and it was clean.
- No repo had unpushed commits or untracked files that were not ignored.

## 3. Reset and clean

```sh
cd ~/repos
git -C Raumfreund stash push -m "pre-clean 2026-11-20"
for r in Raumfreund tb-app ThoraxGPT_from_Wish CroLingo ESP32-Tiny-LLM BavarianLemmings docker_experiments; do
  git -C $r reset --hard -q && git -C $r clean -xfdq
done
```

To get the Raumfreund work back: `git -C ~/repos/Raumfreund stash pop`.

## 4. Results

| Repo | Before | After | What was removed |
|------|-------:|------:|------------------|
| Raumfreund | 9.36 GB | 2.4 GB | `build/`, `.dart_tool/`, `.toolchain/venv`, `dist/` |
| ESP32-Tiny-LLM | 7.83 GB | 39 MB | `.venv-gpu/`, `.venv/`, `node_modules/`, `build/`, generated data |
| CroLingo | 7.74 GB | 2.4 GB | `build/`, `.tooling/trivy-cache`, `.tooling/bin`, `.dart_tool/` |
| ThoraxGPT_from_Wish | 6.93 GB | 7.2 GB | nothing (see step 5) |
| tb-app | 5.72 GB | 31 MB | `.venv/`, `__pycache__/` |
| BavarianLemmings | 2.44 GB | 1.2 GB | orphaned agent-worktree copies in `.claude/worktrees` |
| docker_experiments | 1.28 GB | 0.9 MB | ignored copy of `P118_HMI/` (the real `~/repos/P118_HMI` is untouched) |

`df -h` after the clean: `/home` 807G size, 717G used, 49G free, 94%.

## 5. What the clean did not remove, and why

`git clean` does not delete registered worktrees or nested git repos. Thus these items stay:

- `ThoraxGPT_from_Wish/.claude/worktrees`: about 7.0 GB in 16 agent worktrees.
  The worktree `agent-a97e30bcce02518f3` alone is 5.4 GB.
- `BavarianLemmings/.claude/worktrees`: about 1.2 GB of live worktrees.
  Six have uncommitted changes, and some branches are not merged into `main`.
- `Raumfreund/.toolchain` (2.3 GB) and `CroLingo/.tooling` (2.4 GB): most likely nested repos, such as an SDK clone.

## 6. Open items (decision for the owner)

1. Remove the old worktrees in ThoraxGPT and BavarianLemmings (about 8 GB). First keep or commit the uncommitted changes.
2. Look at the repos that were not cleaned. `ComfyUI` is 29.2 GB and `mpt` is 22.5 GB.
3. Pop or drop the Raumfreund stash `pre-clean 2026-11-20`.
