"""Command-line entry point: video in, unique slide PNGs (+ optional transcript) out."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from . import detect, transcript, video_io
from .dedup import SlideChangeDetector, SlideDecision

logger = logging.getLogger("slide_extractor")


def _positive_float(value: str) -> float:
    parsed = float(value)
    if not parsed > 0:
        raise argparse.ArgumentTypeError(f"must be > 0, got {parsed}")
    return parsed


def _fraction_float(value: str) -> float:
    """A value in (0, 1], for a quantity that's a fraction of a frame dimension."""
    parsed = float(value)
    if not (0 < parsed <= 1):
        raise argparse.ArgumentTypeError(f"must be > 0 and <= 1, got {parsed}")
    return parsed


def _unit_interval_float(value: str) -> float:
    """A value in [0, 1], for an SSIM-like similarity threshold."""
    parsed = float(value)
    if not (0 <= parsed <= 1):
        raise argparse.ArgumentTypeError(f"must be between 0 and 1, got {parsed}")
    return parsed


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {parsed}")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {parsed}")
    return parsed


@dataclass
class Config:
    video: Path
    output: Path
    interval: float
    min_box_frac: float
    top_trim_px: int
    bottom_trim_px: int | None
    border_inset_px: int
    ssim_threshold: float
    min_sharpness: float
    debug: bool
    overwrite: bool
    transcript: bool
    whisper_model: str


def parse_args(argv: list[str] | None = None) -> Config:
    parser = argparse.ArgumentParser(
        description="Extract unique presentation slides from a screen-recorded meeting video."
    )
    parser.add_argument("video", type=Path, help="Path to the recording (e.g. an .mkv file)")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("slides_output"),
        help="Output directory for slide PNGs and manifest (default: ./slides_output)",
    )
    parser.add_argument(
        "--interval", type=_positive_float, default=1.0,
        help="Seconds between sampled frames (default: 1.0)",
    )
    parser.add_argument(
        "--min-box-frac", type=_fraction_float, default=0.5,
        help="Minimum fraction of frame width/height a green row/col span must "
             "cover to count as the real screen-share box (default: 0.5)",
    )
    parser.add_argument(
        "--top-trim-px", type=_non_negative_int, default=42,
        help="Pixels to trim off the top of the detected box to remove browser "
             "chrome/banner; recording-specific, tune with --debug (default: 42)",
    )
    parser.add_argument(
        "--bottom-trim-px", type=_non_negative_int, default=None,
        help="Pixels to trim off the bottom of the detected box to remove "
             "Zoom's letterbox padding below the shared window. Default: "
             "auto-detect the black bar height per frame (it varies "
             "recording to recording, even within one recording). Pass a "
             "fixed value to override auto-detection.",
    )
    parser.add_argument(
        "--border-inset-px", type=_non_negative_int, default=3,
        help="Pixels to inset from the detected green border (default: 3)",
    )
    parser.add_argument(
        "--ssim-threshold", type=_unit_interval_float, default=0.90,
        help="Below this SSIM vs the last accepted slide, a candidate counts as "
             "a new slide (default: 0.90)",
    )
    parser.add_argument(
        "--min-sharpness", type=_non_negative_float, default=0.0005,
        help="Minimum Laplacian-variance sharpness for a candidate to be "
             "considered (rejects blurry mid-transition frames) (default: 0.0005)",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Also dump the raw (untrimmed) box crop for tuning --top-trim-px",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite --output if it already exists",
    )
    parser.add_argument(
        "--transcript", action="store_true",
        help="Also generate a best-effort audio transcript (requires faster-whisper)",
    )
    parser.add_argument(
        "--whisper-model", default="small",
        help="faster-whisper model size (default: small)",
    )
    args = parser.parse_args(argv)
    return Config(
        video=args.video,
        output=args.output,
        interval=args.interval,
        min_box_frac=args.min_box_frac,
        top_trim_px=args.top_trim_px,
        bottom_trim_px=args.bottom_trim_px,
        border_inset_px=args.border_inset_px,
        ssim_threshold=args.ssim_threshold,
        min_sharpness=args.min_sharpness,
        debug=args.debug,
        overwrite=args.overwrite,
        transcript=args.transcript,
        whisper_model=args.whisper_model,
    )


def _clear_previous_outputs(output: Path) -> None:
    """Remove this tool's own artifacts from a prior run.

    A prior run may have used different parameters (e.g. a coarser
    --interval) and produced more slides than this run will. Without this,
    a later, shorter run would leave stale slide_*.png files on disk that
    no longer correspond to any entry in the fresh manifest.json. Only
    files/directories this tool itself creates are touched.
    """
    for stale in output.glob("slide_*.png"):
        stale.unlink()
    for name in ("manifest.json", "transcript.txt", "transcript.srt"):
        stale_file = output / name
        if stale_file.exists():
            stale_file.unlink()
    debug_dir = output / "debug"
    if debug_dir.is_dir():
        for stale in debug_dir.glob("raw_t*.png"):
            stale.unlink()


def _prepare_output_dir(output: Path, overwrite: bool) -> None:
    if output.exists() and not overwrite:
        raise FileExistsError(f"{output} already exists. Pass --overwrite to reuse it.")
    if output.exists():
        _clear_previous_outputs(output)
    output.mkdir(parents=True, exist_ok=True)


def run(config: Config) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not config.video.is_file():
        logger.error("Video file not found: %s", config.video)
        return 1

    _prepare_output_dir(config.output, config.overwrite)
    debug_dir = config.output / "debug"
    if config.debug:
        debug_dir.mkdir(exist_ok=True)

    info = video_io.probe(config.video)
    logger.info(
        "Probed video: %dx%d, %.1fs, ~%.2f fps", info.width, info.height, info.duration_s, info.fps
    )

    detector = SlideChangeDetector(
        ssim_threshold=config.ssim_threshold, min_sharpness=config.min_sharpness
    )

    manifest: list[dict] = []
    scanned = 0
    rejected_no_box = 0
    rejected_blurry = 0
    rejected_duplicate = 0
    slide_index = 0

    for timestamp, frame in video_io.iter_sampled_frames(
        config.video, config.interval, info.width, info.height
    ):
        scanned += 1
        mask = detect.green_mask(frame)
        bbox = detect.find_screen_share_box(mask, min_frac=config.min_box_frac)
        if bbox is None:
            rejected_no_box += 1
            continue

        crop = detect.crop_slide(
            frame, bbox,
            top_trim_px=config.top_trim_px,
            bottom_trim_px=config.bottom_trim_px,
            border_inset_px=config.border_inset_px,
        )

        if config.debug:
            raw_crop = detect.crop_slide(
                frame, bbox, top_trim_px=0, bottom_trim_px=0, border_inset_px=config.border_inset_px
            )
            Image.fromarray(raw_crop).save(debug_dir / f"raw_t{timestamp:08.1f}s.png")

        decision = detector.classify(crop)
        if decision is SlideDecision.BLURRY:
            rejected_blurry += 1
            continue
        if decision is SlideDecision.DUPLICATE:
            rejected_duplicate += 1
            continue

        slide_index += 1
        filename = f"slide_{slide_index:04d}_t{timestamp:08.1f}s.png"
        Image.fromarray(crop).save(config.output / filename)
        manifest.append({"index": slide_index, "timestamp_s": timestamp, "file": filename})
        logger.info("Saved %s (t=%.1fs)", filename, timestamp)

        if scanned % 100 == 0:
            logger.info("...scanned %d frames so far", scanned)

    (config.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    logger.info(
        "Done. Scanned %d frames -> %d slides saved, %d rejected (no screen share), "
        "%d rejected (blurry/transition), %d rejected (duplicate slide).",
        scanned, slide_index, rejected_no_box, rejected_blurry, rejected_duplicate,
    )

    if config.transcript:
        segments = transcript.transcribe(config.video, model_size=config.whisper_model)
        if segments is not None:
            transcript.write_txt(segments, config.output / "transcript.txt")
            transcript.write_srt(segments, config.output / "transcript.srt")
            logger.info("Transcript written to %s", config.output / "transcript.txt")

    return 0


def main(argv: list[str] | None = None) -> int:
    config = parse_args(argv)
    try:
        return run(config)
    except (
        FileExistsError,
        video_io.InvalidVideoError,
        video_io.FfmpegNotFoundError,
        video_io.VideoDecodeError,
    ) as exc:
        logger.error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
