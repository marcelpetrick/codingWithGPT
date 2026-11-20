# 20261120_cleanDisk: free disk space in `~/repos`

**Result:** about 57 GB free again on `/home`. Free space went from about 19 GB to 76 GB (91% used).
Seven repos went from 42.9 GB to 13.2 GB (step 3). ComfyUI went from 29.2 GB to 2.1 GB (step 6).
No commit and no tracked file was lost.

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

## 6. ComfyUI: update, test, then remove the venv and the models

ComfyUI went from 29.2 GB to 2.1 GB. Free space on `/home` is now 76 GB (91% used).

1. Make a backup branch: `git branch backup/myMods-20261120 mpe/myMods`.
2. Merge upstream: `git fetch origin && git merge origin/master` on `mpe/myMods`. This was 395 commits, with no conflicts (`92d0a7a4e`, ComfyUI 0.46.0).
3. Update the dependencies: `uv pip install --python venv/bin/python -r requirements.txt` (torch 2.14.0+cu130).
4. Test: `./generate_image.sh "a red fox sitting in fresh snow, morning light"` gave a correct image in 21 s.
5. On the owner's instruction, remove `venv/` (6.8 GB) and the model files: `rm -rf venv; git clean -xfdq models`.

The removed models (20.6 GB):

| File | Size |
|------|-----:|
| `diffusion_models/qwen_image_2.1_int8_convrot.safetensors` | 6.76 GB |
| `text_encoders/qwen3vl_8b_w4a8.safetensors` | 5.88 GB |
| `diffusion_models/flux-2-klein-4b-fp8.safetensors` | 3.79 GB |
| `text_encoders/qwen_3_4b_fp4_mixed.safetensors` | 3.24 GB |
| `vae/qwen_image_2.1_vae_bf16.safetensors` | 0.63 GB |
| `vae/flux2-vae.safetensors` | 0.31 GB |

Effect: ComfyUI does not run now. `20261109_recreate101ImageGenerations` (Track B), `qwenImage2.1` and
`llmPEG/src/llmpeg/generators.py` need it. To make it run again:

1. Create the venv: `python -m venv venv`.
2. Install the dependencies: `uv pip install --python venv/bin/python -r requirements.txt`.
3. Download the model files above into `models/` again.

The fork remote `github_clone` (`github.com/marcelpetrick/ComfyUI`) returns "Repository not found".
The 5 own commits on `mpe/myMods` exist only on this laptop.

## 7. Open items (decision for the owner)

1. Remove the old worktrees in ThoraxGPT and BavarianLemmings (about 8 GB). First keep or commit the uncommitted changes.
2. Look at `mpt` (22.5 GB). It was not cleaned.
3. Pop or drop the Raumfreund stash `pre-clean 2026-11-20`.
4. Push the ComfyUI branch `mpe/myMods` to a remote that exists, or export it as patches.
5. The rest of ComfyUI is `input/` (1.7 GB), `temp/` and `output/` (200 MB each). Remove them if they are not needed.
