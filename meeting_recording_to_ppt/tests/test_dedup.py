import numpy as np

from slide_extractor.dedup import SlideChangeDetector

RNG = np.random.default_rng(42)


def _textured_slide(base_color: tuple[int, int, int], seed: int) -> np.ndarray:
    """A slide-like image: flat background + deterministic pseudo-text noise."""
    rng = np.random.default_rng(seed)
    img = np.full((400, 700, 3), base_color, dtype=np.uint8)
    # Sprinkle some sharp dark "text" pixels so it isn't perfectly flat (a
    # perfectly flat image has zero Laplacian variance and would always be
    # rejected as "blurry").
    ys = rng.integers(0, 400, size=2000)
    xs = rng.integers(0, 700, size=2000)
    img[ys, xs] = (0, 0, 0)
    return img


def test_first_frame_is_always_new():
    detector = SlideChangeDetector()
    slide = _textured_slide((255, 255, 255), seed=1)
    assert detector.is_new_slide(slide) is True


def test_identical_frame_is_not_new():
    detector = SlideChangeDetector()
    slide = _textured_slide((255, 255, 255), seed=1)
    assert detector.is_new_slide(slide) is True
    assert detector.is_new_slide(slide.copy()) is False


def test_slightly_perturbed_frame_is_not_new():
    detector = SlideChangeDetector(ssim_threshold=0.90)
    slide = _textured_slide((255, 255, 255), seed=1)
    assert detector.is_new_slide(slide) is True

    perturbed = slide.copy()
    # Simulate a moving mouse cursor: a tiny localized change.
    perturbed[10:20, 10:15] = (0, 0, 0)
    assert detector.is_new_slide(perturbed) is False


def test_substantially_different_frame_is_new():
    detector = SlideChangeDetector()
    slide_a = _textured_slide((255, 255, 255), seed=1)
    slide_b = _textured_slide((30, 60, 200), seed=2)

    assert detector.is_new_slide(slide_a) is True
    assert detector.is_new_slide(slide_b) is True


def test_blurry_transition_frame_is_rejected():
    detector = SlideChangeDetector(min_sharpness=0.0005)
    flat = np.full((400, 700, 3), 128, dtype=np.uint8)  # zero-variance, "blurry"
    assert detector.is_new_slide(flat) is False


def test_stricter_threshold_flags_more_changes_as_new():
    slide = _textured_slide((255, 255, 255), seed=1)
    perturbed = slide.copy()
    perturbed[10:20, 10:15] = (0, 0, 0)

    lenient = SlideChangeDetector(ssim_threshold=0.5)
    lenient.is_new_slide(slide)
    assert lenient.is_new_slide(perturbed) is False

    strict = SlideChangeDetector(ssim_threshold=0.999)
    strict.is_new_slide(slide)
    assert strict.is_new_slide(perturbed) is True
