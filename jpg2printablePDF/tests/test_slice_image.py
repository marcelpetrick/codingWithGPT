import os
import shutil
import tempfile
from PIL import Image
import pytest

from main import slice_image, A4_WIDTH_PX, A4_HEIGHT_PX

@pytest.fixture(scope="module")
def temp_dir():
    """Create a temporary directory for test images."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)

def create_test_image(path, width, height, color=(100, 100, 255)):
    """Create a solid-colored test image at given dimensions."""
    img = Image.new("RGB", (width, height), color)
    img.save(path)
    return path

def test_basic_slicing(temp_dir):
    image_path = create_test_image(os.path.join(temp_dir, "basic.jpg"), 100, 3000)
    slices = slice_image(image_path)
    assert len(slices) > 1
    for img in slices:
        assert img.size == (A4_WIDTH_PX, A4_HEIGHT_PX)

def test_exact_height_division(temp_dir):
    step = int(A4_HEIGHT_PX * (1 - 0.05))
    height = step * 3 + int(A4_HEIGHT_PX * 0.05)  # Ensures 3 full + 1 minimal slice
    image_path = create_test_image(os.path.join(temp_dir, "exact.jpg"), 100, height)
    slices = slice_image(image_path)
    assert len(slices) == 4

def test_zero_overlap(temp_dir):
    image_path = create_test_image(os.path.join(temp_dir, "zero.jpg"), 100, A4_HEIGHT_PX * 2)
    slices = slice_image(image_path, overlap_percent=0)
    assert len(slices) == 2

def test_large_overlap(temp_dir):
    image_path = create_test_image(os.path.join(temp_dir, "overlap.jpg"), 100, A4_HEIGHT_PX * 2)
    slices = slice_image(image_path, overlap_percent=49)
    assert len(slices) > 2  # More pages because overlap is large

def test_final_slice_smaller_than_page(temp_dir):
    image_path = create_test_image(os.path.join(temp_dir, "final_small.jpg"), 100, A4_HEIGHT_PX + 200)
    slices = slice_image(image_path)
    assert len(slices) == 2
    assert slices[-1].size == (A4_WIDTH_PX, A4_HEIGHT_PX)
