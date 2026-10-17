I reviewed the diff from `HEAD~2` to `HEAD`, which covers the two Gource commits (the branch has no upstream and there is no `main`; `master...HEAD` gives the same diff). The changes are all media tooling: `linkedin/render-gource.sh`, `linkedin/gource-legend.py`, the docs and the manifest. I found no crash on this machine (Manjaro, with Noto fonts at `/usr/share/fonts/noto`). The findings are about portability, problems that will appear as the history grows, and breaks from the project's media conventions.

10 findings, most severe first:

1. `linkedin/render-gource.sh:20`: The font paths are hardcoded to the Arch/Manjaro location `/usr/share/fonts/noto/...`, both here (`FONT`) and in gource-legend.py (`FONTS`, line 15), so rendering fails on other systems.

   Failure scenario: On Debian/Ubuntu (Noto lives under /usr/share/fonts/truetype/noto), on macOS or in CI, gource cannot load `--font-file` and `ImageFont.truetype` raises OSError, so every preset fails and so does the names legend. Nothing checks for the font or lets the user override the path.

2. `linkedin/render-gource.sh:116`: With `set -u`, expanding the empty array `"${extra[@]}"` is an 'unbound variable' error in bash before 4.4, and `mapfile` (line 165) needs bash 4. The script assumes a new bash but never checks for one.

   Failure scenario: On macOS `/usr/bin/env bash` is usually bash 3.2. There every preset except names aborts at the ffmpeg line with `extra[@]: unbound variable`, and names dies with `mapfile: command not found`.

3. `linkedin/render-gource.sh:28`: Each commit gets one fixed day and `--seconds-per-day` is 9/commits. The ffmpeg output is then cut at `-t 10`, but nothing checks that Gource actually finishes the tree within 9 s, so the claim that the last second holds the finished tree is never verified.

   Failure scenario: Gource keeps running after the last commit because of `--max-file-lag`, final file animations and camera settling, and long commits stretch playback further. Once that passes 10 s, `-t 10` cuts the clip while the tree is still growing, and the script still succeeds. The repo has no frame or last-frame check.

4. `linkedin/render-gource.sh:63`: Every `--name-status` line goes into the Gource custom log unchanged, but Gource's custom format only accepts A/M/D as the type. Git can also emit T (type change) and others, and it quotes paths with special characters.

   Failure scenario: Once the history contains a symlink-to-file change (status `T`) or a file name with non-ASCII characters, the line reads `...|T|path|colour` or `...|M|"d\303\251mo.png"|...`. Gource then rejects or misparses it: the file is shown under a quoted wrong name and gets the Config colour because the extension now ends in `"`.

5. `linkedin/render-gource.sh:73`: `legend_groups` counts files from `git ls-files`, which quotes special paths (core.quotePath). Files with such names are therefore counted under the wrong group.

   Failure scenario: A tracked file such as `docs/ü.png` appears as `"docs/\303\274.png"`. The anchored regex `\.(gif|jpg|png)$` misses it because of the trailing quote, so the legend counts it under Config instead of Images.

6. `scripts/refresh-media.mjs:53`: The new Gource media family is not in refresh-media, which AGENTS.md describes as `npm run refresh-media  # rebuild and refresh every media family`. render-gource.sh also asserts nothing about its outputs, while AGENTS.md says 'Captures must assert the demonstrated outcome'.

   Failure scenario: Running `npm run refresh-media` re-records the other LinkedIn clips but leaves the six gource-*.mp4 files as they were, and their manifest entries keep pointing at an old history. A broken render (truncated or empty) is never caught because the script checks neither frame count nor duration.

7. `linkedin/render-gource.sh:60`: The commit pacing (`1700000000 + 86400 * n`) is written twice, once in the git-log awk (line 31) and once in `coloured_log`, and the two logs come from separate git invocations (line 31 uses `--encoding=UTF-8 --no-show-signature`, `coloured_log` does not).

   Failure scenario: A change to the pacing, the start date or the commit filtering in one place leaves the names clip and the other five clips on different timelines. Simpler: produce a single custom-format log (colour optional) and use it for every preset.

8. `linkedin/render-gource.sh:78`: `legend_groups` runs `git ls-files` plus grep once per group (7 times) and rebuilds the list of all extensions inside the loop, when one pass would do.

   Failure scenario: That is seven full index listings, plus an `all` string rebuilt for the Config group, all to do a classification the `coloured_log` awk already has. A single awk pass over `git ls-files` using the same extension map would give all counts at once and could not drift from the colour mapping.

9. `linkedin/README.md:39`: The new MP4s add about 34 MB of binary video straight into git history, without LFS, and they go stale with every commit because they show the repository's own history.

   Failure scenario: Every refresh adds another ~34 MB to every clone, permanently. Because the clips depict the history, each later commit makes them out of date, which pushes towards frequent re-commits.

10. `docs/tasks.md:179`: The new rows T165 and T166 are placed above T164, so the task table is no longer in id order.

    Failure scenario: AGENTS.md says to 'add new requests' to docs/tasks.md in every commit. Putting them ahead of T164 makes the table out of order and hides the newest entry when scanning from the bottom.

---
Final text:
I reviewed the diff from `HEAD~2` to `HEAD`, which covers the two Gource commits (the branch has no upstream and there is no `main`; `master...HEAD` gives the same diff). The changes are all media tooling: `linkedin/render-gource.sh`, `linkedin/gource-legend.py`, the docs and the manifest. I found no crash on this machine (Manjaro, with Noto fonts at `/usr/share/fonts/noto`). The findings are about portability, problems that will appear as the history grows, and breaks from the project's media conventions.

10 findings, most severe first:

1. `linkedin/render-gource.sh:20`: The font paths are hardcoded to the Arch/Manjaro location `/usr/share/fonts/noto/...`, both here (`FONT`) and in gource-legend.py (`FONTS`, line 15), so rendering fails on other systems.

   Failure scenario: On Debian/Ubuntu (Noto lives under /usr/share/fonts/truetype/noto), on macOS or in CI, gource cannot load `--font-file` and `ImageFont.truetype` raises OSError, so every preset fails and so does the names legend. Nothing checks for the font or lets the user override the path.

2. `linkedin/render-gource.sh:116`: With `set -u`, expanding the empty array `"${extra[@]}"` is an 'unbound variable' error in bash before 4.4, and `mapfile` (line 165) needs bash 4. The script assumes a new bash but never checks for one.

   Failure scenario: On macOS `/usr/bin/env bash` is usually bash 3.2. There every preset except names aborts at the ffmpeg line with `extra[@]: unbound variable`, and names dies with `mapfile: command not found`.

3. `linkedin/render-gource.sh:28`: Each commit gets one fixed day and `--seconds-per-day` is 9/commits. The ffmpeg output is then cut at `-t 10`, but nothing checks that Gource actually finishes the tree within 9 s, so the claim that the last second holds the finished tree is never verified.

   Failure scenario: Gource keeps running after the last commit because of `--max-file-lag`, final file animations and camera settling, and long commits stretch playback further. Once that passes 10 s, `-t 10` cuts the clip while the tree is still growing, and the script still succeeds. The repo has no frame or last-frame check.

4. `linkedin/render-gource.sh:63`: Every `--name-status` line goes into the Gource custom log unchanged, but Gource's custom format only accepts A/M/D as the type. Git can also emit T (type change) and others, and it quotes paths with special characters.

   Failure scenario: Once the history contains a symlink-to-file change (status `T`) or a file name with non-ASCII characters, the line reads `...|T|path|colour` or `...|M|"d\303\251mo.png"|...`. Gource then rejects or misparses it: the file is shown under a quoted wrong name and gets the Config colour because the extension now ends in `"`.

5. `linkedin/render-gource.sh:73`: `legend_groups` counts files from `git ls-files`, which quotes special paths (core.quotePath). Files with such names are therefore counted under the wrong group.

   Failure scenario: A tracked file such as `docs/ü.png` appears as `"docs/\303\274.png"`. The anchored regex `\.(gif|jpg|png)$` misses it because of the trailing quote, so the legend counts it under Config instead of Images.

6. `scripts/refresh-media.mjs:53`: The new Gource media family is not in refresh-media, which AGENTS.md describes as `npm run refresh-media  # rebuild and refresh every media family`. render-gource.sh also asserts nothing about its outputs, while AGENTS.md says 'Captures must assert the demonstrated outcome'.

   Failure scenario: Running `npm run refresh-media` re-records the other LinkedIn clips but leaves the six gource-*.mp4 files as they were, and their manifest entries keep pointing at an old history. A broken render (truncated or empty) is never caught because the script checks neither frame count nor duration.

7. `linkedin/render-gource.sh:60`: The commit pacing (`1700000000 + 86400 * n`) is written twice, once in the git-log awk (line 31) and once in `coloured_log`, and the two logs come from separate git invocations (line 31 uses `--encoding=UTF-8 --no-show-signature`, `coloured_log` does not).

   Failure scenario: A change to the pacing, the start date or the commit filtering in one place leaves the names clip and the other five clips on different timelines. Simpler: produce a single custom-format log (colour optional) and use it for every preset.

8. `linkedin/render-gource.sh:78`: `legend_groups` runs `git ls-files` plus grep once per group (7 times) and rebuilds the list of all extensions inside the loop, when one pass would do.

   Failure scenario: That is seven full index listings, plus an `all` string rebuilt for the Config group, all to do a classification the `coloured_log` awk already has. A single awk pass over `git ls-files` using the same extension map would give all counts at once and could not drift from the colour mapping.

9. `linkedin/README.md:39`: The new MP4s add about 34 MB of binary video straight into git history, without LFS, and they go stale with every commit because they show the repository's own history.

   Failure scenario: Every refresh adds another ~34 MB to every clone, permanently. Because the clips depict the history, each later commit makes them out of date, which pushes towards frequent re-commits.

10. `docs/tasks.md:179`: The new rows T165 and T166 are placed above T164, so the task table is no longer in id order.

    Failure scenario: AGENTS.md says to 'add new requests' to docs/tasks.md in every commit. Putting them ahead of T164 makes the table out of order and hides the newest entry when scanning from the bottom.
