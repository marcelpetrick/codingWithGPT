import numpy as np

from slide_extractor.dedup import SlideChangeDetector, SlideDecision

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
    assert detector.classify(slide) is SlideDecision.NEW


def test_identical_frame_is_a_duplicate():
    detector = SlideChangeDetector()
    slide = _textured_slide((255, 255, 255), seed=1)
    assert detector.classify(slide) is SlideDecision.NEW
    assert detector.classify(slide.copy()) is SlideDecision.DUPLICATE


def test_slightly_perturbed_frame_is_a_duplicate():
    detector = SlideChangeDetector(ssim_threshold=0.90)
    slide = _textured_slide((255, 255, 255), seed=1)
    assert detector.classify(slide) is SlideDecision.NEW

    perturbed = slide.copy()
    # Simulate a moving mouse cursor: a tiny localized change.
    perturbed[10:20, 10:15] = (0, 0, 0)
    assert detector.classify(perturbed) is SlideDecision.DUPLICATE


def test_substantially_different_frame_is_new():
    detector = SlideChangeDetector()
    slide_a = _textured_slide((255, 255, 255), seed=1)
    slide_b = _textured_slide((30, 60, 200), seed=2)

    assert detector.classify(slide_a) is SlideDecision.NEW
    assert detector.classify(slide_b) is SlideDecision.NEW


def test_blurry_transition_frame_is_rejected_as_blurry_not_duplicate():
    detector = SlideChangeDetector(min_sharpness=0.0005)
    flat = np.full((400, 700, 3), 128, dtype=np.uint8)  # zero-variance, "blurry"
    assert detector.classify(flat) is SlideDecision.BLURRY


def test_blurry_frame_does_not_update_state_or_count_as_duplicate_later():
    detector = SlideChangeDetector(min_sharpness=0.0005)
    flat = np.full((400, 700, 3), 128, dtype=np.uint8)
    assert detector.classify(flat) is SlideDecision.BLURRY

    # A blurry rejection must not be treated as "the last seen slide" --
    # the next real, sharp frame is still a genuinely new slide, not a
    # duplicate of the discarded blurry one.
    slide = _textured_slide((255, 255, 255), seed=1)
    assert detector.classify(slide) is SlideDecision.NEW


def test_stricter_threshold_flags_more_changes_as_new():
    slide = _textured_slide((255, 255, 255), seed=1)
    perturbed = slide.copy()
    perturbed[10:20, 10:15] = (0, 0, 0)

    lenient = SlideChangeDetector(ssim_threshold=0.5)
    lenient.classify(slide)
    assert lenient.classify(perturbed) is SlideDecision.DUPLICATE

    strict = SlideChangeDetector(ssim_threshold=0.999)
    strict.classify(slide)
    assert strict.classify(perturbed) is SlideDecision.NEW
