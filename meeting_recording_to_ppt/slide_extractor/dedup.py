"""Decide whether a cropped slide candidate is visually new or a repeat.

Two signals are used:

1. **Sharpness** (variance of the Laplacian): frames captured mid-transition
   (slide animations, cross-fades) are noticeably blurrier than a settled
   slide. Blurry candidates are rejected outright so they never get
   compared against -- or saved as -- a "new" slide.
2. **SSIM** against the last accepted slide: a genuinely new slide differs
   substantially in structure; the same slide with only cursor movement or
   minor rendering noise stays above the similarity threshold.
"""

from __future__ import annotations

from enum import Enum

import numpy as np
from scipy import ndimage
from skimage.color import rgb2gray
from skimage.metrics import structural_similarity
from skimage.transform import resize


class SlideDecision(Enum):
    """Why a candidate crop was, or wasn't, saved as a new slide.

    Kept distinct rather than collapsed into a single bool: a run that
    saves zero slides for a "too blurry" reason needs a different fix
    (loosen --min-sharpness) than one where everything is a "duplicate"
    (loosen --ssim-threshold or check --top-trim-px/--bottom-trim-px
    aren't cropping the wrong region) -- conflating the two into one
    counter made that impossible to tell apart from the summary log line.
    """

    NEW = "new"
    BLURRY = "blurry"
    DUPLICATE = "duplicate"

# Fixed target shape (not aspect-ratio-preserving): the detected screen-share
# box can jitter by a pixel or two between frames (antialiasing at the green
# border edge), which would otherwise make consecutive crops incomparable in
# shape. Comparisons only care about relative structure, so a minor aspect
# distortion from resizing every candidate to the same shape is harmless.
_COMPARE_SHAPE = (180, 320)


def _to_comparable(image: np.ndarray) -> np.ndarray:
    """Grayscale + downsize an image to a fixed shape for fast comparison."""
    gray = rgb2gray(image) if image.ndim == 3 else image.astype(np.float64)
    if gray.shape[0] == 0 or gray.shape[1] == 0:
        raise ValueError("cannot compare an empty image")
    return resize(gray, _COMPARE_SHAPE, anti_aliasing=True)


def sharpness_score(image: np.ndarray) -> float:
    """Higher is sharper; low values indicate a blurry/transition frame."""
    comparable = _to_comparable(image)
    return float(ndimage.laplace(comparable).var())


class SlideChangeDetector:
    """Stateful gate that flags a crop as a new slide at most once per change."""

    def __init__(self, ssim_threshold: float = 0.90, min_sharpness: float = 0.0005):
        self.ssim_threshold = ssim_threshold
        self.min_sharpness = min_sharpness
        self._last: np.ndarray | None = None

    def classify(self, candidate: np.ndarray) -> SlideDecision:
        """Classify ``candidate``, updating internal state if it's a new slide."""
        comparable = _to_comparable(candidate)

        if float(ndimage.laplace(comparable).var()) < self.min_sharpness:
            return SlideDecision.BLURRY  # blurry / mid-transition frame

        if self._last is None:
            self._last = comparable
            return SlideDecision.NEW

        similarity = structural_similarity(
            self._last, comparable, data_range=1.0
        )
        if similarity < self.ssim_threshold:
            self._last = comparable
            return SlideDecision.NEW
        return SlideDecision.DUPLICATE
