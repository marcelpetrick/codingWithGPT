"""
main.py

A Python script to slice a tall image into A4-sized segments with overlaps,
and export them into a multi-page PDF suitable for printing.

Usage:
    python main.py image.jpg
"""

import sys
import os
from PIL import Image
from fpdf import FPDF

# A4 dimensions in points (1 point = 1/72 inch)
A4_WIDTH_PT = 595  # 8.27 inch
A4_HEIGHT_PT = 842  # 11.69 inch

# A4 dimensions in pixels at 300 DPI
DPI = 300
A4_WIDTH_PX = int(8.27 * DPI)
A4_HEIGHT_PX = int(11.69 * DPI)

# Default overlap in percentage
DEFAULT_OVERLAP_PERCENT = 10

def slice_image(image_path, overlap_percent=DEFAULT_OVERLAP_PERCENT, save_parts=False, output_dir="slices"):
    """
    Slice a tall image vertically to fit A4 pages with overlap.

    :param image_path: Path to the input image file.
    :param overlap_percent: Percentage of vertical overlap between slices.
    :param save_parts: If True, saves each slice as an image file.
    :param output_dir: Directory to save slices if save_parts is True.
    :return: List of PIL.Image slices.
    """
    image = Image.open(image_path)
    original_width, original_height = image.size

    # Resize image to A4 width while maintaining aspect ratio
    scale_factor = A4_WIDTH_PX / original_width
    new_width = A4_WIDTH_PX
    new_height = int(original_height * scale_factor)
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)

    overlap_px = int(A4_HEIGHT_PX * (overlap_percent / 100))
    step = A4_HEIGHT_PX - overlap_px

    slices = []
    top = 0
    slice_index = 1

    if save_parts:
        os.makedirs(output_dir, exist_ok=True)

    while top < new_height:
        bottom = top + A4_HEIGHT_PX
        if bottom > new_height:
            bottom = new_height
            top = max(0, bottom - A4_HEIGHT_PX)  # Adjust top for final page

        slice_img = resized_image.crop((0, top, new_width, bottom))

        # Paste onto blank A4-sized white canvas
        canvas = Image.new("RGB", (A4_WIDTH_PX, A4_HEIGHT_PX), "white")
        paste_y = (A4_HEIGHT_PX - slice_img.height) // 2 if slice_img.height < A4_HEIGHT_PX else 0
        canvas.paste(slice_img, (0, paste_y))
        slices.append(canvas)

        # Optionally save the slice
        if save_parts:
            filename = os.path.join(output_dir, f"slice_{slice_index:03d}.jpg")
            canvas.save(filename, "JPEG")
            print(f"Saved {filename}")
            slice_index += 1

        if bottom == new_height:
            break
        top += step

    return slices

import tempfile

def images_to_pdf(images, output_path):
    """
    Save a list of PIL.Image objects to a multi-page PDF.

    :param images: List of PIL.Image objects.
    :param output_path: Path to the output PDF file.
    """
    pdf = FPDF(unit="pt", format=[A4_WIDTH_PT, A4_HEIGHT_PT])
    temp_files = []

    try:
        for idx, img in enumerate(images):
            pdf.add_page()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                img.save(tmp.name, "JPEG")
                pdf.image(tmp.name, x=0, y=0, w=A4_WIDTH_PT, h=A4_HEIGHT_PT)
                temp_files.append(tmp.name)
        pdf.output(output_path)
    finally:
        # Clean up all temp files
        for path in temp_files:
            try:
                os.remove(path)
            except Exception:
                pass

def main():
    """
    Main function to parse command-line arguments and execute the slicing and PDF generation.
    """
    if len(sys.argv) < 2:
        print("Usage: python main.py image.jpg")
        sys.exit(1)

    image_path = sys.argv[1]

    if not os.path.isfile(image_path):
        print(f"File not found: {image_path}")
        sys.exit(1)

    try:
        slices = slice_image(image_path, save_parts=True)
        output_pdf_path = os.path.splitext(image_path)[0] + "_sliced.pdf"
        images_to_pdf(slices, output_pdf_path)
        print(f"PDF saved to {output_pdf_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
