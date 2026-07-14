import numpy as np

from slide_extractor.detect import (
    BBox,
    crop_slide,
    find_screen_share_box,
    green_mask,
    measure_bottom_letterbox,
)
from tests.conftest import GREEN, draw_rect_border

WIDTH, HEIGHT = 1920, 1080


def _blank_frame() -> np.ndarray:
    return np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)


def test_finds_large_screen_share_box():
    frame = _blank_frame()
    draw_rect_border(frame, left=302, right=1618, top=258, bottom=1080, color=GREEN)

    bbox = find_screen_share_box(green_mask(frame))

    assert bbox is not None
    assert bbox.left == 302
    assert bbox.right == 1617
    assert bbox.top == 258
    assert bbox.bottom == 1079


def test_no_box_when_no_green_present():
    frame = _blank_frame()
    frame[:] = (120, 100, 95)  # skin-tone-ish talking head background

    assert find_screen_share_box(green_mask(frame)) is None


def test_small_thumbnail_border_alone_is_rejected():
    frame = _blank_frame()
    # Simulates the small active-speaker thumbnail border only (no slide shared).
    draw_rect_border(frame, left=854, right=1065, top=140, bottom=258, color=GREEN)

    assert find_screen_share_box(green_mask(frame)) is None


def test_thumbnail_border_does_not_corrupt_real_box_even_when_adjacent():
    frame = _blank_frame()
    # Real screen-share box.
    draw_rect_border(frame, left=302, right=1618, top=258, bottom=1080, color=GREEN)
    # Small active-speaker thumbnail border sitting directly above it, touching
    # the same row range -- this is the exact merge scenario found in the
    # real recording (verified via connected-component analysis) that a naive
    # global-bounding-box approach gets wrong.
    draw_rect_border(frame, left=854, right=1065, top=140, bottom=259, color=GREEN)

    bbox = find_screen_share_box(green_mask(frame))

    assert bbox is not None
    assert bbox.top == 258, "top should be the real box, not the thumbnail's 140"
    assert bbox.left == 302
    assert bbox.right == 1617


def test_min_frac_threshold_rejects_medium_boxes():
    frame = _blank_frame()
    # A box spanning only 30% of width/height should not qualify at the
    # default 0.5 min_frac.
    draw_rect_border(frame, left=800, right=1300, top=400, bottom=700, color=GREEN)

    assert find_screen_share_box(green_mask(frame), min_frac=0.5) is None
    assert find_screen_share_box(green_mask(frame), min_frac=0.2) is not None


def test_crop_slide_applies_inset_and_top_trim():
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    frame[:] = (10, 10, 10)
    frame[300:1080, 305:1615] = (255, 255, 255)  # slide content area
    bbox = BBox(left=302, right=1617, top=258, bottom=1079)

    crop = crop_slide(frame, bbox, top_trim_px=42, border_inset_px=3)

    assert crop.shape[0] == 1079 - 3 - (258 + 3 + 42)
    assert crop.shape[1] == (1617 - 3) - (302 + 3)
    # The crop should be entirely the white slide content, not the dark margin.
    assert (crop == 255).all()


def test_measure_bottom_letterbox_finds_black_bar():
    frame = np.full((1080, 1920, 3), (10, 10, 10), dtype=np.uint8)
    bbox = BBox(left=302, right=1617, top=258, bottom=1079)
    frame[300:1042, 305:1615] = (255, 255, 255)  # content
    frame[1042:1079, 305:1615] = 0  # letterbox bar, 37px tall

    trim = measure_bottom_letterbox(frame, bbox, border_inset_px=3)

    assert trim == 1079 - 3 - 1042


def test_measure_bottom_letterbox_zero_when_content_reaches_bottom():
    frame = np.full((1080, 1920, 3), (10, 10, 10), dtype=np.uint8)
    bbox = BBox(left=302, right=1617, top=258, bottom=1079)
    frame[300:1079, 305:1615] = (255, 255, 255)  # content all the way down

    assert measure_bottom_letterbox(frame, bbox, border_inset_px=3) == 0


def test_crop_slide_auto_detects_bottom_letterbox():
    frame = np.full((1080, 1920, 3), (10, 10, 10), dtype=np.uint8)
    bbox = BBox(left=302, right=1617, top=258, bottom=1079)
    frame[300:1042, 305:1615] = (255, 255, 255)
    frame[1042:1079, 305:1615] = 0

    crop = crop_slide(frame, bbox, top_trim_px=42, border_inset_px=3)

    assert (crop == 255).all(), "auto bottom-trim should exclude the black letterbox bar"
