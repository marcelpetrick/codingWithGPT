import json

from slide_extractor.cli import main
from tests.conftest import requires_ffmpeg

pytestmark = requires_ffmpeg


def test_end_to_end_extracts_only_the_two_unique_slides(synthetic_slide_recording, tmp_path):
    out_dir = tmp_path / "out"

    exit_code = main(
        [
            str(synthetic_slide_recording),
            "-o", str(out_dir),
            "--interval", "0.4",
            "--min-box-frac", "0.5",
            "--top-trim-px", "0",
            "--border-inset-px", "5",
            "--ssim-threshold", "0.9",
            "--min-sharpness", "0.00001",
        ]
    )

    assert exit_code == 0

    slide_files = sorted(out_dir.glob("slide_*.png"))
    assert len(slide_files) == 2, f"expected 2 unique slides, got {[f.name for f in slide_files]}"

    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert len(manifest) == 2
    assert manifest[0]["index"] == 1
    assert manifest[1]["index"] == 2
    assert manifest[0]["timestamp_s"] < manifest[1]["timestamp_s"]


def test_refuses_to_overwrite_existing_output_without_flag(synthetic_slide_recording, tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    exit_code = main([str(synthetic_slide_recording), "-o", str(out_dir)])

    assert exit_code == 1
    assert not list(out_dir.glob("slide_*.png"))


def test_missing_video_file_returns_error(tmp_path):
    exit_code = main([str(tmp_path / "nope.mkv"), "-o", str(tmp_path / "out")])
    assert exit_code == 1


def test_corrupt_video_file_returns_error_not_a_traceback(tmp_path):
    garbage = tmp_path / "garbage.mkv"
    garbage.write_bytes(b"this is not a real video file, just some bytes")

    exit_code = main([str(garbage), "-o", str(tmp_path / "out")])

    assert exit_code == 1


def test_overwrite_clears_stale_slides_from_a_previous_run(synthetic_slide_recording, tmp_path):
    out_dir = tmp_path / "out"
    common_args = [
        str(synthetic_slide_recording),
        "-o", str(out_dir),
        "--interval", "0.4",
        "--min-box-frac", "0.5",
        "--top-trim-px", "0",
        "--border-inset-px", "5",
        "--ssim-threshold", "0.9",
        "--min-sharpness", "0.00001",
    ]

    assert main(common_args) == 0
    assert len(list(out_dir.glob("slide_*.png"))) == 2

    # Simulate a leftover artifact from an earlier run with different
    # parameters that produced more slides than this run will.
    stale = out_dir / "slide_9999_t999.0s.png"
    stale.write_bytes(b"not a real png, just a leftover marker")

    assert main(common_args + ["--overwrite"]) == 0

    slide_files = sorted(out_dir.glob("slide_*.png"))
    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert not stale.exists(), "stale slide from a previous run must be removed on --overwrite"
    assert len(slide_files) == len(manifest) == 2
