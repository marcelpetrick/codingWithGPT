# Agentic engineering parodies

Two fictional English subtitle scripts turn an El Risitas interview into jokes about review queues and CI runners. The Spanish audio is unchanged. The captions are parody, not a translation.

## Videos

- `output/merge-hell.mp4`: agents create pull requests faster than reviewers can clear them.
- `output/automated-review.mp4`: agents create review loops and overload CI runners.

The source is Juan Joya Borja with Jesús Quintero on Canal Sur's *Ratones Coloraos*. The downloaded source is [El Risitas, no subtitles](https://www.dailymotion.com/video/x6jtfj8). The available source is 328×248. The export enlarges it for the subtitle canvas, but cannot restore image detail. Check reuse rights and platform rules before publishing.

The captions use automatic reading-time timing. They have not been checked against every speech turn or laugh. Review them in a video player and adjust the timing before publication.

## Make another version

1. Install Python 3, FFmpeg with libass and libx264, and DejaVu Sans.
2. Copy a file in `versions/` to a new JSON file.
3. Set `title`, `source_start`, and `duration` in seconds.
4. Write each subtitle card as one plain text string in `cards`.
5. Keep each card within two lines of 36 characters after wrapping.
6. Run `python3 scripts/render.py versions/YOUR-VERSION.json --source source/el-risitas-clean.mp4`.
7. Check the MP4 in `output/` and edit the cards as needed.

The script creates SRT and ASS files in `subtitles/`. Use `--captions-only` to create them without a video. It rejects cards that do not fit or do not have enough reading time. The generator assigns timing automatically. To tune individual cues, edit the generated ASS and SRT files together, then use FFmpeg with the ASS file. Running the generator again overwrites both files.

The source file was downloaded with `yt-dlp -f hls-380 -o source/el-risitas-clean.mp4 https://www.dailymotion.com/video/x6jtfj8`. Availability and permissions can change.
