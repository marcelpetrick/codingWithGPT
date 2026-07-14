from slide_extractor.transcript import (
    TranscriptSegment,
    _format_srt_timestamp,
    is_available,
    write_srt,
    write_txt,
)

# These cover the pure, dependency-free parts of transcript.py (timestamp
# formatting, file writers). transcribe() itself needs faster-whisper plus
# ffmpeg audio extraction and is exercised end-to-end via localPipeline.sh
# instead, not here.


def test_is_available_returns_a_bool():
    assert isinstance(is_available(), bool)


def test_format_srt_timestamp_zero():
    assert _format_srt_timestamp(0.0) == "00:00:00,000"


def test_format_srt_timestamp_sub_second():
    assert _format_srt_timestamp(1.234) == "00:00:01,234"


def test_format_srt_timestamp_minutes_and_hours():
    # 1h 2m 3.5s
    assert _format_srt_timestamp(3723.5) == "01:02:03,500"


def test_format_srt_timestamp_rounds_milliseconds():
    assert _format_srt_timestamp(0.9996) == "00:00:01,000"


def test_write_txt_joins_nonempty_segments(tmp_path):
    segments = [
        TranscriptSegment(start_s=0.0, end_s=1.0, text="Hello"),
        TranscriptSegment(start_s=1.0, end_s=1.5, text=""),  # silence, no text
        TranscriptSegment(start_s=1.5, end_s=3.0, text="world"),
    ]
    out_path = tmp_path / "transcript.txt"

    write_txt(segments, out_path)

    assert out_path.read_text(encoding="utf-8") == "Hello\nworld"


def test_write_srt_formats_index_timerange_and_text(tmp_path):
    segments = [
        TranscriptSegment(start_s=0.0, end_s=2.5, text="Hello there"),
        TranscriptSegment(start_s=2.5, end_s=4.0, text="General Kenobi"),
    ]
    out_path = tmp_path / "transcript.srt"

    write_srt(segments, out_path)

    assert out_path.read_text(encoding="utf-8") == (
        "1\n"
        "00:00:00,000 --> 00:00:02,500\n"
        "Hello there\n"
        "\n"
        "2\n"
        "00:00:02,500 --> 00:00:04,000\n"
        "General Kenobi\n"
    )
