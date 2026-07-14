# Architecture

How `slide_extractor` turns a screen-recorded meeting video into a
deduplicated set of slide PNGs (and, optionally, a transcript), and how
`localPipeline.sh` sets up and verifies all of it locally.

## Module map

```mermaid
graph LR
    cli["cli.py<br/>argparse + orchestration"]
    video_io["video_io.py<br/>ffmpeg/ffprobe subprocess wrappers"]
    detect["detect.py<br/>green-box detection + crop"]
    dedup["dedup.py<br/>sharpness + SSIM gate"]
    transcript["transcript.py<br/>optional faster-whisper transcript"]

    cli --> video_io
    cli --> detect
    cli --> dedup
    cli --> transcript
    transcript --> video_io

    style cli fill:#4c6ef5,color:#fff
    style video_io fill:#495057,color:#fff
    style detect fill:#495057,color:#fff
    style dedup fill:#495057,color:#fff
    style transcript fill:#868e96,color:#fff
```

`cli.py` is the only module that imports the other four; they don't
depend on each other except `transcript.py`, which reuses
`video_io.extract_audio`. This keeps each concern independently testable
(see `tests/test_detect.py`, `tests/test_dedup.py`, `tests/test_video_io.py`,
`tests/test_transcript.py` — none of them need the full CLI wired up).

## Per-frame pipeline

Every sampled frame goes through the same decision chain. Most frames are
discarded early (talking-head segments have no green box at all); only
frames that pass every gate get written to disk.

```mermaid
flowchart TD
    A["ffmpeg: sample 1 frame every --interval seconds"] --> B["green_mask(frame)"]
    B --> C{"find_screen_share_box()<br/>large enough green row/col span?"}
    C -- "no" --> D["discard: not a screen-share frame<br/>(talking head / gallery / meeting-ended freeze-frame)"]
    C -- "yes" --> E["crop_slide()<br/>inset border, trim chrome banner,<br/>auto-trim bottom letterbox"]
    E --> F{"SlideChangeDetector.classify()"}
    F -- "BLURRY<br/>(low Laplacian variance)" --> G["discard: mid-transition frame"]
    F -- "DUPLICATE<br/>(SSIM >= threshold vs last saved)" --> H["discard: same slide as before"]
    F -- "NEW" --> I["save slide_NNNN_tTTTT.png<br/>append manifest.json entry"]

    style I fill:#2f9e44,color:#fff
    style D fill:#adb5bd,color:#000
    style G fill:#adb5bd,color:#000
    style H fill:#adb5bd,color:#000
```

Rejections are counted separately (`rejected_no_box`, `rejected_blurry`,
`rejected_duplicate`) precisely so a run that produces fewer slides than
expected can be diagnosed from the log line alone instead of guessing:

- Mostly `rejected_no_box` → the recording rarely/never had an active,
  pinned screen share (or the Zoom highlight border isn't there for some
  other reason — see `README.md` limitations).
- Nonzero `rejected_blurry` dominating → `--min-sharpness` is too strict
  for this recording's slide style; lower it.
- `rejected_duplicate` dominating when slides *are* visibly changing →
  `--ssim-threshold` is too lenient, or the crop region itself is wrong
  (check `--debug` output, `--top-trim-px`/`--bottom-trim-px`).

## Why green-box detection works (and the pitfall it avoids)

```mermaid
flowchart LR
    subgraph naive["Naive: bounding box of ALL green pixels"]
        n1["thumbnail border<br/>(small, top strip)"] --> n2["merged bbox<br/>(wrong — includes face strip)"]
        n3["real screen-share border<br/>(large, center)"] --> n2
    end

    subgraph actual["Used: row/col green-pixel SPAN"]
        a1["thumbnail border row span<br/>≈ 200px — below min_frac threshold"] -.->|"filtered out"| a3["discarded"]
        a2["screen-share border row span<br/>≈ 1300px — exceeds min_frac × frame width"] --> a4["real bbox"]
    end
```

`find_screen_share_box()` doesn't take the bounding box of every green
pixel in the frame — that would merge Zoom's small active-speaker
thumbnail border with the real screen-share border whenever they sit on
adjacent rows (verified to happen in the reference recording). Instead it
looks at each row's/column's green-pixel *span*: only the real
screen-share rectangle's border rows/columns span a large fraction of the
frame (`--min-box-frac`, default 0.5); the thumbnail border's rows/columns
never do. See `slide_extractor/detect.py` and `tests/test_detect.py`'s
`test_thumbnail_border_does_not_corrupt_real_box_even_when_adjacent` for
the exact scenario this guards against.

## CLI run sequence

```mermaid
sequenceDiagram
    participant User
    participant cli as cli.main()
    participant vio as video_io
    participant det as detect
    participant dd as dedup.SlideChangeDetector
    participant tr as transcript

    User->>cli: python -m slide_extractor video.mkv -o out/
    cli->>cli: parse_args() — validates ranges, exits 2 on bad input
    cli->>cli: _prepare_output_dir() — clears stale outputs if --overwrite
    cli->>vio: probe(video)
    vio-->>cli: VideoInfo(width, height, duration, fps)
    loop for each sampled frame
        cli->>vio: iter_sampled_frames(...)
        vio-->>cli: (timestamp, frame)
        cli->>det: green_mask(frame), find_screen_share_box(mask)
        det-->>cli: BBox or None
        cli->>det: crop_slide(frame, bbox)
        det-->>cli: cropped slide image
        cli->>dd: classify(crop)
        dd-->>cli: NEW / BLURRY / DUPLICATE
        alt NEW
            cli->>cli: save PNG, append manifest entry
        end
    end
    cli->>cli: write manifest.json
    opt --transcript
        cli->>tr: transcribe(video, model_size)
        tr->>vio: extract_audio(video) -> temp wav
        tr-->>cli: segments or None (best-effort)
        cli->>cli: write transcript.txt / transcript.srt
    end
    cli-->>User: exit 0 (success) / exit 1 (known or unexpected error) / exit 2 (bad arguments)
```

## `localPipeline.sh` stages

```mermaid
flowchart TD
    P["Check ffmpeg/ffprobe on PATH"] --> V["Create/reuse .venv"]
    V --> C["Install requirements.txt"]
    C --> DEV["Install requirements-dev.txt<br/>(pytest, pytest-cov)"]
    DEV --> T{"--no-transcript?"}
    T -- "no (default)" --> TR["Install requirements-transcript.txt<br/>(faster-whisper)"]
    T -- "yes" --> SKIP1["skip"]
    TR --> TEST["pytest + coverage<br/>-> htmlcov/, junit.xml, coverage.xml"]
    SKIP1 --> TEST
    TEST --> OPEN["Open htmlcov/index.html<br/>(best-effort, non-gating)"]
    OPEN --> SMOKE["CLI smoke check: --help"]
    SMOKE --> E2E["End-to-end smoke test:<br/>synthetic clip -> slides + manifest"]
    E2E --> REAL{"--with-real-video<br/>and a .mkv/.mp4 present?"}
    REAL -- "yes" --> RV["Run full pipeline against it<br/>(informational only, non-gating)"]
    REAL -- "no" --> SKIP2["skip"]
    RV --> SUM["Print PASS/FAIL/SKIP summary"]
    SKIP2 --> SUM

    style SUM fill:#4c6ef5,color:#fff
```

Only the stages up through **E2E** gate the script's exit code (plus
Transcript Deps, unless `--no-transcript` was passed). Coverage-report
opening and the real-video check are informational and never fail the
run — the real recording used to develop this tool is intentionally
`.gitignore`d, so a fresh checkout must be able to fully verify itself
without it.

## Key design decisions

| Decision | Why |
|---|---|
| Detect slides via Zoom's green screen-share border, not a fixed screen region | The border's position is stable within one recording but the *box itself* isn't always the same size (letterbox padding varies) — cropping a fixed pixel rectangle would silently break whenever a presenter's window changed. |
| Stream frames from ffmpeg via a `rawvideo` pipe rather than writing per-frame image files | A multi-hour recording sampled every second would otherwise mean thousands of temp PNG/JPEG files; piping keeps this to one subprocess and no disk churn. |
| SSIM + Laplacian-variance dedup instead of exact/hash-based comparison | Cursor movement and minor rendering noise must **not** count as a new slide, but genuine content changes must. A perceptual, structure-aware comparison tolerates the former and catches the latter; a byte-exact or simple pixel-diff comparison would not. |
| `SlideDecision` enum instead of a bool | A run producing too few slides needs a different fix depending on *why* frames were rejected (too blurry vs. genuinely duplicate) — collapsing both into one counter made that undiagnosable from the log alone. |
| Transcript generation is fully optional and best-effort | It's explicitly a secondary goal; a missing dependency, a failed model load, or a transcription error must never prevent the (primary) slide extraction from succeeding. |
| All destructive test fixtures are synthetic, generated at test time | Keeps the suite fast and deterministic, and avoids ever committing real meeting audio/video/faces to the repository. |
