Base: master @ ed5235a   Head: bac0bbb
Files changed: 15   +389 / -8 lines

**Findings**

```
#1  LOW  Code  linkedin/render-gource.sh:20
    The font directory is hard-coded to Arch/Manjaro's `/usr/share/fonts/noto` (here and in `linkedin/gource-legend.py:15`). On Debian/Ubuntu (`/usr/share/fonts/truetype/noto`) or macOS, every preset fails: gource rejects `--font-file` and Pillow raises `OSError`, but the README lists only gource, ffmpeg and Pillow as requirements. Resolve the font at runtime, for example with `fc-match -f '%{file}' 'Noto Sans:bold'` passed through to the Python script, or allow an override such as `FONT_DIR=…`.
```

```
#2  LOW  Code  linkedin/render-gource.sh:72
    `legend_groups` counts files with `git ls-files`, which reads the index, while the tree in the video comes from `git log` of HEAD. Files that are staged but not committed, or deleted but not yet staged, make the legend counts differ from what the clip shows. Count from `git ls-tree -r --name-only HEAD` here and on line 78, so both sides use the same snapshot.
```

```
#3  LOW  Architecture  linkedin/
    About 34 MB of rendered MP4s are committed, roughly a fifth of the current 162 MB `.git`. These clips show the repository's own history, so they are out of date after the next commit, and every refresh adds another ~34 MB to history permanently. Consider keeping them as release assets or in Git LFS and committing only `render-gource.sh` and `gource-legend.py`.
```

I checked the main risk of overlapping options by pulling frames out of the committed clips. When a preset repeats `--hide`, the later value wins, so file names do appear in `gource-names.mp4`. The legend overlay and the `--key` on the wide clip also render correctly. The colour mapping in the awk script agrees with the legend's grep-based counts, including the Config fallback and files without an extension. Prettier and markdownlint pass on the changed documents.

**Verdict:** Mergeable as it stands. None of these block it: the changes are tooling and media outside the game, and all three findings are portability or hygiene fixes for later.

---
Final text:
Base: master @ ed5235a   Head: bac0bbb
Files changed: 15   +389 / -8 lines

**Findings**

```
#1  LOW  Code  linkedin/render-gource.sh:20
    The font directory is hard-coded to Arch/Manjaro's `/usr/share/fonts/noto` (here and in `linkedin/gource-legend.py:15`). On Debian/Ubuntu (`/usr/share/fonts/truetype/noto`) or macOS, every preset fails: gource rejects `--font-file` and Pillow raises `OSError`, but the README lists only gource, ffmpeg and Pillow as requirements. Resolve the font at runtime, for example with `fc-match -f '%{file}' 'Noto Sans:bold'` passed through to the Python script, or allow an override such as `FONT_DIR=…`.
```

```
#2  LOW  Code  linkedin/render-gource.sh:72
    `legend_groups` counts files with `git ls-files`, which reads the index, while the tree in the video comes from `git log` of HEAD. Files that are staged but not committed, or deleted but not yet staged, make the legend counts differ from what the clip shows. Count from `git ls-tree -r --name-only HEAD` here and on line 78, so both sides use the same snapshot.
```

```
#3  LOW  Architecture  linkedin/
    About 34 MB of rendered MP4s are committed, roughly a fifth of the current 162 MB `.git`. These clips show the repository's own history, so they are out of date after the next commit, and every refresh adds another ~34 MB to history permanently. Consider keeping them as release assets or in Git LFS and committing only `render-gource.sh` and `gource-legend.py`.
```

I checked the main risk of overlapping options by pulling frames out of the committed clips. When a preset repeats `--hide`, the later value wins, so file names do appear in `gource-names.mp4`. The legend overlay and the `--key` on the wide clip also render correctly. The colour mapping in the awk script agrees with the legend's grep-based counts, including the Config fallback and files without an extension. Prettier and markdownlint pass on the changed documents.

**Verdict:** Mergeable as it stands. None of these block it: the changes are tooling and media outside the game, and all three findings are portability or hygiene fixes for later.
