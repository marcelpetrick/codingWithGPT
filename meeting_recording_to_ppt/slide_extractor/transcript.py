"""Optional best-effort audio transcript via faster-whisper.

This is a minor/secondary feature: its absence (missing optional dependency,
or a transcription failure) must never prevent slide extraction from
succeeding. Callers should treat ``transcribe`` returning ``None`` as "skip
the transcript, log why, move on."
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from . import video_io

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranscriptSegment:
    start_s: float
    end_s: float
    text: str


def is_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def transcribe(
    video_path: Path | str, model_size: str = "small"
) -> list[TranscriptSegment] | None:
    """Extract audio and transcribe it. Returns ``None`` if unavailable/failed."""
    if not is_available():
        logger.warning(
            "faster-whisper is not installed; skipping transcript. "
            "Install it with: pip install -r requirements-transcript.txt"
        )
        return None

    import tempfile

    from faster_whisper import WhisperModel

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = Path(tmp_dir) / "audio.wav"
            video_io.extract_audio(video_path, wav_path)

            logger.info("Loading whisper model '%s'...", model_size)
            model = WhisperModel(model_size, device="cpu", compute_type="int8")

            segments, _info = model.transcribe(str(wav_path))
            return [
                TranscriptSegment(start_s=seg.start, end_s=seg.end, text=seg.text.strip())
                for seg in segments
            ]
    except Exception:
        logger.exception("Transcript generation failed; continuing without it.")
        return None


def _format_srt_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_txt(segments: list[TranscriptSegment], out_path: Path | str) -> None:
    out_path = Path(out_path)
    out_path.write_text(
        "\n".join(seg.text for seg in segments if seg.text), encoding="utf-8"
    )


def write_srt(segments: list[TranscriptSegment], out_path: Path | str) -> None:
    out_path = Path(out_path)
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(
            f"{_format_srt_timestamp(seg.start_s)} --> {_format_srt_timestamp(seg.end_s)}"
        )
        lines.append(seg.text)
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
