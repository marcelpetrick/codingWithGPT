import os
import shutil
import logging
from PIL import Image
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg', '.webp', '.wbp', '.png')

def create_output_folder(folder_path: str) -> None:
    """Create folder if it doesn't exist."""
    os.makedirs(folder_path, exist_ok=True)
    logger.debug(f"Output folder checked/created at: {folder_path}")

def get_image_files(directory: str) -> List[str]:
    """Return a list of supported image files in a directory."""
    return [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and f.lower().endswith(SUPPORTED_EXTENSIONS)
    ]

def convert_to_png(src_path: str, dest_path: str) -> None:
    """Convert an image to PNG and save it to dest_path."""
    try:
        with Image.open(src_path) as img:
            img = img.convert('RGBA')
            img.save(dest_path, 'PNG', optimize=True)
            logger.info(f"Converted {src_path} -> {dest_path}")
    except Exception as e:
        logger.error(f"Failed to convert {src_path}: {e}")
        raise

def copy_png(src_path: str, dest_path: str) -> None:
    """Copy PNG file to destination."""
    try:
        shutil.copy2(src_path, dest_path)
        logger.info(f"Copied {src_path} -> {dest_path}")
    except Exception as e:
        logger.error(f"Failed to copy {src_path}: {e}")
        raise

def process_images(input_dir: str = '.', output_dir: str = 'png') -> None:
    """Process all images in input_dir and output PNGs to output_dir."""
    create_output_folder(output_dir)
    image_files = get_image_files(input_dir)

    logger.info(f"Found {len(image_files)} image(s) to process.")

    for file_name in image_files:
        src_path = os.path.join(input_dir, file_name)
        base_name = os.path.splitext(file_name)[0]
        dest_path = os.path.join(output_dir, f"{base_name}.png")

        if file_name.lower().endswith('.png'):
            copy_png(src_path, dest_path)
        else:
            convert_to_png(src_path, dest_path)

    logger.info("Processing complete!")

if __name__ == "__main__":
    process_images()
