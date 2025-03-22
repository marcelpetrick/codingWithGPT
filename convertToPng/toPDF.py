import os
import time
from PIL import Image

TARGET_SIZE = (1080, 1080)
BACKGROUND_COLOR = (255, 255, 255)  # White background

def get_sorted_png_files(directory: str):
    """Return a sorted list of PNG files in the given directory."""
    return sorted(
        (f for f in os.listdir(directory) if f.lower().endswith(".png")),
        key=str.lower
    )

def resize_and_pad_image(image: Image.Image, size=(1080, 1080), background=(255, 255, 255)) -> Image.Image:
    """
    Resize an image to fit within 'size' while maintaining aspect ratio.
    Pad with 'background' color to make it exactly 'size'.
    """
    img_ratio = image.width / image.height
    target_ratio = size[0] / size[1]

    if img_ratio > target_ratio:
        new_width = size[0]
        new_height = round(size[0] / img_ratio)
    else:
        new_height = size[1]
        new_width = round(size[1] * img_ratio)

    resized_image = image.resize((new_width, new_height), Image.LANCZOS)

    new_image = Image.new("RGB", size, background)
    paste_position = (
        (size[0] - new_width) // 2,
        (size[1] - new_height) // 2
    )
    new_image.paste(resized_image, paste_position)

    return new_image

def create_pdf_from_pngs(directory: str, output_pdf: str):
    png_files = get_sorted_png_files(directory)

    if not png_files:
        print("No PNG files found in the directory.")
        return

    images = []

    for file_name in png_files:
        file_path = os.path.join(directory, file_name)
        with Image.open(file_path) as img:
            img_rgb = img.convert("RGB")
            processed_img = resize_and_pad_image(img_rgb, TARGET_SIZE, BACKGROUND_COLOR)
            images.append(processed_img)

    images[0].save(
        output_pdf,
        "PDF",
        resolution=300.0,
        save_all=True,
        append_images=images[1:]
    )

    print(f"PDF created successfully: {output_pdf}")

def generate_output_filename(prefix="result", extension="pdf") -> str:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"

if __name__ == "__main__":
    output_pdf_name = generate_output_filename()
    create_pdf_from_pngs(".", output_pdf_name)
