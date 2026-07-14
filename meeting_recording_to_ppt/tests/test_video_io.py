import subprocess

import pytest

from slide_extractor import video_io
from tests.conftest import requires_ffmpeg

pytestmark = requires_ffmpeg


@pytest.fixture
def synthetic_clip(tmp_path):
    clip_path = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=3:r=10",
            "-pix_fmt", "yuv420p",
            "-loglevel", "error",
            str(clip_path),
        ],
        check=True,
    )
    return clip_path


def test_probe_returns_expected_metadata(synthetic_clip):
    info = video_io.probe(synthetic_clip)
    assert info.width == 320
    assert info.height == 240
    assert info.duration_s == pytest.approx(3.0, abs=0.2)
    assert info.fps == pytest.approx(10.0, rel=0.1)


def test_probe_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        video_io.probe(tmp_path / "does_not_exist.mp4")


def test_probe_non_video_file_raises_invalid_video_error(tmp_path):
    garbage = tmp_path / "garbage.mkv"
    garbage.write_bytes(b"this is not a real video file, just some bytes")

    with pytest.raises(video_io.InvalidVideoError):
        video_io.probe(garbage)


def test_iter_sampled_frames_yields_expected_count_and_shape(synthetic_clip):
    info = video_io.probe(synthetic_clip)
    frames = list(
        video_io.iter_sampled_frames(synthetic_clip, interval_s=1.0, width=info.width, height=info.height)
    )

    # ~3s clip sampled every 1s -> 3 frames (0.0, 1.0, 2.0).
    assert len(frames) == 3
    timestamps = [t for t, _ in frames]
    assert timestamps == [0.0, 1.0, 2.0]
    for _, frame in frames:
        assert frame.shape == (240, 320, 3)
        # Solid blue color=blue -> low red/green, high-ish blue channel.
        assert frame[..., 2].mean() > frame[..., 0].mean()


def test_iter_sampled_frames_generator_can_be_closed_early(synthetic_clip):
    info = video_io.probe(synthetic_clip)
    gen = video_io.iter_sampled_frames(synthetic_clip, interval_s=0.1, width=info.width, height=info.height)
    next(gen)
    gen.close()  # must not raise / hang


def test_iter_sampled_frames_raises_on_ffmpeg_failure_instead_of_yielding_nothing(synthetic_clip):
    info = video_io.probe(synthetic_clip)
    # interval_s=0 makes ffmpeg's "fps=1/0" filter fail to initialize, so
    # ffmpeg exits with an error before producing any frames. Before this
    # was fixed, that looked identical to "clean end of stream" and the
    # generator silently yielded zero frames instead of raising.
    with pytest.raises(video_io.VideoDecodeError):
        list(video_io.iter_sampled_frames(synthetic_clip, interval_s=0, width=info.width, height=info.height))
