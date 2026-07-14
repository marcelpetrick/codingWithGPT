import pytest

from slide_extractor.cli import parse_args

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
