Base: master @ ed5235a   Head: bac0bbb
Files changed: 15   +389 / -8 lines

**Findings**

```
#1  LOW  Code  linkedin/render-gource.sh:20
    FONT (and FONTS in linkedin/gource-legend.py:15) hard-codes the Arch/Manjaro Noto path /usr/share/fonts/noto. On Debian/Ubuntu the font lives under /usr/share/fonts/truetype/noto, so Gource and Pillow's truetype() both fail there, and the README's dependency list doesn't mention the font. Resolve the font with `fc-match -f '%{file}' 'Noto Sans:bold'`, or allow an environment override, and pass the result to the Python helper.
```

The rest of the branch checked out:
- **Gource log:** this repository's history yields only A, M and D statuses, with no merges and no quoted paths. The custom log in the `names` preset is therefore valid, and its timing matches the git log the other five presets use.
- **Names clip:** a frame from `gource-names.mp4` shows file names and the legend, so the second `--hide` overrides the one in `common` as intended.
- **Licensing and lint:** `linkedin/*.mp4` is already annotated in `REUSE.toml`, the new `.sh` and `.py` files carry SPDX headers, and Prettier and markdownlint pass on the changed docs.
- **SPDX lint crash:** `scripts/spdx.mjs` crashes in this checkout, but the cause is the untracked `node_modules` symlink, not this branch.

**Verdict**

Mergeable as it stands. #1 is a portability fix for the offline render script and does not block.

---
Final text:
Base: master @ ed5235a   Head: bac0bbb
Files changed: 15   +389 / -8 lines

**Findings**

```
#1  LOW  Code  linkedin/render-gource.sh:20
    FONT (and FONTS in linkedin/gource-legend.py:15) hard-codes the Arch/Manjaro Noto path /usr/share/fonts/noto. On Debian/Ubuntu the font lives under /usr/share/fonts/truetype/noto, so Gource and Pillow's truetype() both fail there, and the README's dependency list doesn't mention the font. Resolve the font with `fc-match -f '%{file}' 'Noto Sans:bold'`, or allow an environment override, and pass the result to the Python helper.
```

The rest of the branch checked out:
- **Gource log:** this repository's history yields only A, M and D statuses, with no merges and no quoted paths. The custom log in the `names` preset is therefore valid, and its timing matches the git log the other five presets use.
- **Names clip:** a frame from `gource-names.mp4` shows file names and the legend, so the second `--hide` overrides the one in `common` as intended.
- **Licensing and lint:** `linkedin/*.mp4` is already annotated in `REUSE.toml`, the new `.sh` and `.py` files carry SPDX headers, and Prettier and markdownlint pass on the changed docs.
- **SPDX lint crash:** `scripts/spdx.mjs` crashes in this checkout, but the cause is the untracked `node_modules` symlink, not this branch.

**Verdict**

Mergeable as it stands. #1 is a portability fix for the offline render script and does not block.
