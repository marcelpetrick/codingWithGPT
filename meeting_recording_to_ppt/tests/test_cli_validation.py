import pytest

from slide_extractor import cli
from slide_extractor.cli import main, parse_args

# Argument parsing/validation is pure argparse logic and needs neither
# ffmpeg nor a real video file, unlike the rest of tests/test_cli.py.


@pytest.mark.parametrize(
    "args",
    [
        ["video.mkv", "--interval", "0"],
        ["video.mkv", "--interval", "-1"],
        ["video.mkv", "--min-box-frac", "0"],
        ["video.mkv", "--min-box-frac", "1.5"],
        ["video.mkv", "--min-box-frac", "-0.1"],
        ["video.mkv", "--ssim-threshold", "-0.1"],
        ["video.mkv", "--ssim-threshold", "1.1"],
        ["video.mkv", "--min-sharpness", "-1"],
        ["video.mkv", "--top-trim-px", "-1"],
        ["video.mkv", "--bottom-trim-px", "-1"],
        ["video.mkv", "--border-inset-px", "-1"],
    ],
)
def test_rejects_out_of_range_values(args):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(args)
    assert exc_info.value.code == 2


@pytest.mark.parametrize(
    "args",
    [
        ["video.mkv"],
        ["video.mkv", "--interval", "0.1"],
        ["video.mkv", "--min-box-frac", "1.0"],
        ["video.mkv", "--ssim-threshold", "0"],
        ["video.mkv", "--ssim-threshold", "1"],
        ["video.mkv", "--min-sharpness", "0"],
        ["video.mkv", "--top-trim-px", "0"],
        ["video.mkv", "--bottom-trim-px", "0"],
    ],
)
def test_accepts_boundary_values(args):
    config = parse_args(args)
    assert config.video.name == "video.mkv"


def test_bottom_trim_px_defaults_to_none_for_auto_detection():
    config = parse_args(["video.mkv"])
    assert config.bottom_trim_px is None


def test_unexpected_error_returns_1_instead_of_raising(tmp_path, monkeypatch, caplog):
    video = tmp_path / "video.mkv"
    video.write_bytes(b"placeholder")

    def _boom(*_args, **_kwargs):
        raise RuntimeError("disk exploded")

    monkeypatch.setattr(cli.video_io, "probe", _boom)

    with caplog.at_level("ERROR", logger="slide_extractor"):
        exit_code = main([str(video), "-o", str(tmp_path / "out")])

    assert exit_code == 1
    assert any("Unexpected error" in record.getMessage() for record in caplog.records)
