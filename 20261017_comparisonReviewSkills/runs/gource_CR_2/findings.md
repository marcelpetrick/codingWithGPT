10 findings, most severe first:

1. `linkedin/gource-legend.py:15`: The font directory is hard-coded to the Arch/Manjaro Noto path `/usr/share/fonts/noto`. `render-gource.sh` line 20 does the same with `FONT=/usr/share/fonts/noto/NotoSans-Bold.ttf`.

   Failure scenario: On Debian/Ubuntu (fonts in /usr/share/fonts/truetype/noto), macOS or CI, `ImageFont.truetype` raises OSError and gource cannot load `--font-file`. Under `set -e` every preset aborts, including the five that do not need Python. Nothing checks the path or lets you override it (for example with an env var or `fc-match`).

2. `linkedin/render-gource.sh:50`: The custom log trusts that author names contain no '|' and that `--name-status` only emits A/M/D with unquoted paths. Gource's custom format has none of these protections.

   Failure scenario: Any of these produces malformed or rejected log lines, so files are missing or misplaced in the clip: a contributor or mailmap name with '|'; a type-change entry ('T', e.g. a file replaced by a symlink); or a path with non-ASCII characters, which git quotes as "docs/\303\244.md" under the default core.quotePath. Today's history happens to avoid all three (one author, only A/M/D, no quoted paths), so the bug is latent.

3. `linkedin/render-gource.sh:29`: `git log` stderr is discarded with 2>/dev/null under `set -euo pipefail`. If git fails, the script exits non-zero with no message. The same applies to `coloured_log` on line 50.

   Failure scenario: Running outside a repo, in a shallow clone with a bad ref, or with a git config error makes the script stop silently before rendering. No diagnostic is printed and no MP4 is written.

4. `linkedin/render-gource.sh:32`: The commit count used for pacing comes from `git rev-list --count HEAD`, but the logs come from separate `git log` runs. The two can disagree, and the result is never checked.

   Failure scenario: Gource takes longer to start than expected, or the playback runs past 10 s. `-t $DURATION` then cuts the clip before the finished tree. The 'last second holds the finished tree' promise is never checked, so a truncated clip is still committed and recorded in the manifest.

5. `linkedin/render-gource.sh:69`: Files are grouped by extension twice, in different languages: the awk map in `coloured_log` colours the video, and grep regexes in `legend_groups` count the legend. `legend_groups` also runs `git ls-files` once per group and rebuilds the `all` list inside the loop.

   Failure scenario: Any change to one classifier but not the other (case folding, a new extension rule, dotfile handling) makes the legend counts disagree with the video colours. Each render also runs `git ls-files` 7 times. Fix: classify once (one awk pass over `git ls-files` with the same map) and reuse it.

6. `linkedin/render-gource.sh:59`: Two pipelines each rewrite commit timestamps to one-day steps (the awk on `--raw` output at line 31 and `coloured_log`), so two log formats and two pacing rules have to be kept in step.

   Failure scenario: A change to the pacing (for example 1700000000 + 86400*n) has to be made in two places, or the 'names' clip runs at a different pace from the other five. Simpler: generate the custom log once and use `--log-format custom` for every preset, leaving the colour field empty for the presets that don't colour files.

7. `docs/MEDIA.md:74`: `render-gource.sh` is listed as a media owner, but the 'Reproduce the entire refresh' section, its dependency list (gource, Pillow, Noto fonts) and `npm run refresh-media` do not include it.

   Failure scenario: AGENTS.md says: "Refresh affected screenshots, weapon/feature GIFs and social captions when visible rules change; update the manifest with the generated files." The Gource clips show repository history, so they go stale with every commit, yet `npm run refresh-media` never regenerates them. The manifest keeps hashing old clips, and a contributor following the documented refresh cannot reproduce them.

8. `docs/MEDIA.md:100`: MEDIA.md still says social videos 'keep the existing 1080×1350, H.264/AAC format' with a silent audio track. The new Gource social clips have no audio stream and are 1080×1080 and 1920×1080.

   Failure scenario: The docs now contradict the checked-in assets: the Gource MP4s have no audio stream (the linkedin README says 'without audio'), and three of them are not 1080×1350. Anyone checking media against MEDIA.md, or extending media-manifest checks to match it, sees the mismatch.

9. `linkedin/render-gource.sh:172`: The script needs bash 4.4+ (`mapfile`, and `"${extra[@]}"` on an empty array under `set -u`), but the shebang is `/usr/bin/env bash` and nothing checks the version.

   Failure scenario: On macOS's default bash 3.2, the non-overlay presets die with 'extra[@]: unbound variable' in `render`, and the names preset fails with 'mapfile: command not found'.

10. `docs/tasks.md:179`: The new rows T165 and T166 were inserted above T164, which breaks the table's chronological ID order.

    Failure scenario: AGENTS.md says `docs/tasks.md` should hold 'Every request with status and version'. With the rows out of order, T164 (1.83.3) appears after T166 (1.83.5), so reading down the table no longer follows the request and version history.

---
Final text:
10 findings, most severe first:

1. `linkedin/gource-legend.py:15`: The font directory is hard-coded to the Arch/Manjaro Noto path `/usr/share/fonts/noto`. `render-gource.sh` line 20 does the same with `FONT=/usr/share/fonts/noto/NotoSans-Bold.ttf`.

   Failure scenario: On Debian/Ubuntu (fonts in /usr/share/fonts/truetype/noto), macOS or CI, `ImageFont.truetype` raises OSError and gource cannot load `--font-file`. Under `set -e` every preset aborts, including the five that do not need Python. Nothing checks the path or lets you override it (for example with an env var or `fc-match`).

2. `linkedin/render-gource.sh:50`: The custom log trusts that author names contain no '|' and that `--name-status` only emits A/M/D with unquoted paths. Gource's custom format has none of these protections.

   Failure scenario: Any of these produces malformed or rejected log lines, so files are missing or misplaced in the clip: a contributor or mailmap name with '|'; a type-change entry ('T', e.g. a file replaced by a symlink); or a path with non-ASCII characters, which git quotes as "docs/\303\244.md" under the default core.quotePath. Today's history happens to avoid all three (one author, only A/M/D, no quoted paths), so the bug is latent.

3. `linkedin/render-gource.sh:29`: `git log` stderr is discarded with 2>/dev/null under `set -euo pipefail`. If git fails, the script exits non-zero with no message. The same applies to `coloured_log` on line 50.

   Failure scenario: Running outside a repo, in a shallow clone with a bad ref, or with a git config error makes the script stop silently before rendering. No diagnostic is printed and no MP4 is written.

4. `linkedin/render-gource.sh:32`: The commit count used for pacing comes from `git rev-list --count HEAD`, but the logs come from separate `git log` runs. The two can disagree, and the result is never checked.

   Failure scenario: Gource takes longer to start than expected, or the playback runs past 10 s. `-t $DURATION` then cuts the clip before the finished tree. The 'last second holds the finished tree' promise is never checked, so a truncated clip is still committed and recorded in the manifest.

5. `linkedin/render-gource.sh:69`: Files are grouped by extension twice, in different languages: the awk map in `coloured_log` colours the video, and grep regexes in `legend_groups` count the legend. `legend_groups` also runs `git ls-files` once per group and rebuilds the `all` list inside the loop.

   Failure scenario: Any change to one classifier but not the other (case folding, a new extension rule, dotfile handling) makes the legend counts disagree with the video colours. Each render also runs `git ls-files` 7 times. Fix: classify once (one awk pass over `git ls-files` with the same map) and reuse it.

6. `linkedin/render-gource.sh:59`: Two pipelines each rewrite commit timestamps to one-day steps (the awk on `--raw` output at line 31 and `coloured_log`), so two log formats and two pacing rules have to be kept in step.

   Failure scenario: A change to the pacing (for example 1700000000 + 86400*n) has to be made in two places, or the 'names' clip runs at a different pace from the other five. Simpler: generate the custom log once and use `--log-format custom` for every preset, leaving the colour field empty for the presets that don't colour files.

7. `docs/MEDIA.md:74`: `render-gource.sh` is listed as a media owner, but the 'Reproduce the entire refresh' section, its dependency list (gource, Pillow, Noto fonts) and `npm run refresh-media` do not include it.

   Failure scenario: AGENTS.md says: "Refresh affected screenshots, weapon/feature GIFs and social captions when visible rules change; update the manifest with the generated files." The Gource clips show repository history, so they go stale with every commit, yet `npm run refresh-media` never regenerates them. The manifest keeps hashing old clips, and a contributor following the documented refresh cannot reproduce them.

8. `docs/MEDIA.md:100`: MEDIA.md still says social videos 'keep the existing 1080×1350, H.264/AAC format' with a silent audio track. The new Gource social clips have no audio stream and are 1080×1080 and 1920×1080.

   Failure scenario: The docs now contradict the checked-in assets: the Gource MP4s have no audio stream (the linkedin README says 'without audio'), and three of them are not 1080×1350. Anyone checking media against MEDIA.md, or extending media-manifest checks to match it, sees the mismatch.

9. `linkedin/render-gource.sh:172`: The script needs bash 4.4+ (`mapfile`, and `"${extra[@]}"` on an empty array under `set -u`), but the shebang is `/usr/bin/env bash` and nothing checks the version.

   Failure scenario: On macOS's default bash 3.2, the non-overlay presets die with 'extra[@]: unbound variable' in `render`, and the names preset fails with 'mapfile: command not found'.

10. `docs/tasks.md:179`: The new rows T165 and T166 were inserted above T164, which breaks the table's chronological ID order.

    Failure scenario: AGENTS.md says `docs/tasks.md` should hold 'Every request with status and version'. With the rows out of order, T164 (1.83.3) appears after T166 (1.83.5), so reading down the table no longer follows the request and version history.
