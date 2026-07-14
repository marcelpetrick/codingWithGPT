"""Detect the Zoom screen-share region within a frame and crop out the slide.

Zoom draws a thin, saturated green border around whatever screen share is
currently pinned/viewed. That border is present throughout every slide
segment of a recording and absent during talking-head/gallery segments,
which makes it a reliable, cheap signal for "this frame contains a slide."

The naive approach -- bounding box of all green-ish pixels -- is wrong: Zoom
also draws a small green border around the active speaker's video thumbnail,
and when that thumbnail sits directly above the screen-share box the two
bounding boxes merge. Instead we look for the rows/columns whose green pixel
*span* covers a large fraction of the frame -- only the real screen-share
rectangle's border rows/columns do that; the thumbnail border's rows/columns
have a much smaller span and are filtered out.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# Single source of truth for these tuning knobs -- the CLI's argparse
# defaults (slide_extractor/cli.py) import and reuse them rather than
# repeating the literal values, so the two can't silently drift apart.
DEFAULT_MIN_BOX_FRAC = 0.5
DEFAULT_TOP_TRIM_PX = 42
DEFAULT_BORDER_INSET_PX = 3

# Below this, in either dimension, a crop is almost certainly not usable
# slide content -- most likely --top-trim-px/--bottom-trim-px/
# --border-inset-px are misconfigured for this recording (see README
# "Tuning for a new recording"), silently producing a near-empty PNG
# instead of a slide.
_MIN_REASONABLE_CROP_PX = 20


@dataclass(frozen=True)
class BBox:
    left: int
    right: int
    top: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def green_mask(frame: np.ndarray) -> np.ndarray:
    """Boolean mask of pixels matching Zoom's screen-share border green."""
    r = frame[:, :, 0].astype(np.int16)
    g = frame[:, :, 1].astype(np.int16)
    b = frame[:, :, 2].astype(np.int16)
    return (g > 100) & (g > r * 1.3) & (g > b * 1.3)


def find_screen_share_box(mask: np.ndarray, min_frac: float = DEFAULT_MIN_BOX_FRAC) -> BBox | None:
    """Find the large screen-share rectangle in a green pixel mask.

    Returns ``None`` if no row/column has a green span covering at least
    ``min_frac`` of the frame's width/height respectively (i.e. no active
    screen share is visible in this frame).
    """
    height, width = mask.shape
    if not mask.any():
        return None

    xs = np.arange(width)
    ys = np.arange(height)

    row_max_x = np.where(mask, xs[None, :], -1).max(axis=1)
    row_min_x = np.where(mask, xs[None, :], width).min(axis=1)
    row_span = row_max_x - row_min_x
    valid_rows = row_span > min_frac * width

    col_max_y = np.where(mask, ys[:, None], -1).max(axis=0)
    col_min_y = np.where(mask, ys[:, None], height).min(axis=0)
    col_span = col_max_y - col_min_y
    valid_cols = col_span > min_frac * height

    if not valid_rows.any() or not valid_cols.any():
        return None

    row_idx = np.where(valid_rows)[0]
    col_idx = np.where(valid_cols)[0]
    return BBox(
        left=int(col_idx.min()),
        right=int(col_idx.max()),
        top=int(row_idx.min()),
        bottom=int(row_idx.max()),
    )


def measure_bottom_letterbox(
    frame: np.ndarray, bbox: BBox, border_inset_px: int = DEFAULT_BORDER_INSET_PX,
    max_px: int = 150, black_threshold: int = 12,
) -> int:
    """Measure the height of a solid-black letterbox bar at the bottom of ``bbox``.

    Zoom pads the shared window into the share box at whatever aspect ratio
    it was captured at; when that doesn't match the box's own aspect ratio,
    a solid black bar appears below the actual content. Its height is *not*
    constant across a recording (verified: it varies between 0 and ~37px in
    the reference recording depending on how the presenter's window was
    sized), so it's measured per-frame rather than taken as a fixed offset.
    """
    left = bbox.left + border_inset_px
    right = bbox.right - border_inset_px
    bottom = bbox.bottom - border_inset_px
    top_limit = max(bbox.top, bottom - max_px)

    row_means = frame[top_limit:bottom, left:right].mean(axis=(1, 2))
    trim = 0
    for value in row_means[::-1]:
        if value > black_threshold:
            break
        trim += 1
    return trim


def crop_slide(
    frame: np.ndarray,
    bbox: BBox,
    top_trim_px: int = DEFAULT_TOP_TRIM_PX,
    bottom_trim_px: int | None = None,
    border_inset_px: int = DEFAULT_BORDER_INSET_PX,
) -> np.ndarray:
    """Crop ``frame`` to the slide content inside ``bbox``.

    ``border_inset_px`` strips the green border line itself; ``top_trim_px``
    additionally removes the browser tab/address bar + Zoom's "You are
    viewing..." banner sitting above the actual slide content. ``bottom_trim_px``
    removes letterbox padding Zoom adds below the shared window; leave it as
    ``None`` (default) to auto-detect it per frame via
    :func:`measure_bottom_letterbox`, or pass a fixed int to override.
    """
    height, width = frame.shape[:2]
    if bottom_trim_px is None:
        bottom_trim_px = measure_bottom_letterbox(frame, bbox, border_inset_px)

    left = min(bbox.left + border_inset_px, width - 1)
    right = max(bbox.right - border_inset_px, left + 1)
    top = min(bbox.top + border_inset_px + top_trim_px, height - 1)
    bottom = max(bbox.bottom - border_inset_px - bottom_trim_px, top + 1)

    crop_width, crop_height = right - left, bottom - top
    if crop_width < _MIN_REASONABLE_CROP_PX or crop_height < _MIN_REASONABLE_CROP_PX:
        logger.warning(
            "Crop is only %dx%d px (detected box was %dx%d) -- --top-trim-px/"
            "--bottom-trim-px/--border-inset-px are likely too large for this "
            "recording. Re-run with --debug and check slides_output/debug/.",
            crop_width, crop_height, bbox.width, bbox.height,
        )
    return frame[top:bottom, left:right]
