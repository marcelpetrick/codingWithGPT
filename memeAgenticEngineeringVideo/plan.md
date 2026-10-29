# Video production plan

## Verdict

Both parody scripts and the reusable renderer are ready. The source has low resolution. Caption timing uses reading time and needs a human playback review.

## Plan

1. Commit the supplied meme plan. Estimate: 2 minutes.
2. Find and inspect clean source footage. Estimate: 15 minutes.
3. Build reusable subtitle and video tools. Estimate: 30 minutes.
4. Time and render both parodies. Estimate: 30 minutes.
5. Check both videos and commit the results. Estimate: 15 minutes.

## Status

| Time | Result |
| --- | --- |
| 2026-10-29 | Read the repository instructions and the supplied scripts. |
| 2026-10-29 | Committed the supplied plan and this working plan. |
| 2026-10-29 | Downloaded the source. Sampled frames show the intended interview without visible subtitles. |
| 2026-10-29 | Created two editable scripts and a reusable renderer. |
| 2026-10-29 | Started both exports. |

## Results

The source is 328×248 at 25 fps. The renderer enlarges it to fit a canvas with a separate subtitle band. The captions use reading-time timing. They are not matched to every speech or laugh boundary.

## Resume here

Work in `memeAgenticEngineeringVideo` on the current branch. Check `git status --short`. Run `python3 scripts/render.py versions/merge-hell.json` and `python3 scripts/render.py versions/automated-review.json` to rebuild. Run `ffprobe -v error -show_streams output/merge-hell.mp4` to inspect an export. Review both exports in a player for timing and sound.
