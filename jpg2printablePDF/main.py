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
DEFAULT_OVERLAP_PERCENT = 5

def slice_image(image_path, overlap_percent=DEFAULT_OVERLAP_PERCENT):
    """
    Slice a tall image vertically to fit A4 pages with overlap.

    :param image_path: Path to the input image file.
    :param overlap_percent: Percentage of vertical overlap between slices.
    :return: List of PIL.Image slices.
    """
    image = Image.open(image_path)
    width, height = image.size

    if width > A4_WIDTH_PX:
        raise ValueError("Image width exceeds A4 width at 300 DPI. Please resize manually.")

    overlap_px = int(A4_HEIGHT_PX * (overlap_percent / 100))
    step = A4_HEIGHT_PX - overlap_px

    slices = []
    for top in range(0, height, step):
        bottom = min(top + A4_HEIGHT_PX, height)
        slice_img = image.crop((0, top, width, bottom))
        # Create a blank A4-sized white canvas
        canvas = Image.new("RGB", (A4_WIDTH_PX, A4_HEIGHT_PX), "white")
        offset_x = (A4_WIDTH_PX - width) // 2
        canvas.paste(slice_img, (offset_x, 0))
        slices.append(canvas)
        if bottom == height:
            break

    return slices

def images_to_pdf(images, output_path):
    """
    Save a list of PIL.Image objects to a multi-page PDF.

    :param images: List of PIL.Image objects.
    :param output_path: Path to the output PDF file.
    """
    pdf = FPDF(unit="pt", format=[A4_WIDTH_PT, A4_HEIGHT_PT])
    for img in images:
        pdf.add_page()
        temp_path = "_temp_page.jpg"
        img.save(temp_path, "JPEG")
        pdf.image(temp_path, x=0, y=0, w=A4_WIDTH_PT, h=A4_HEIGHT_PT)
        os.remove(temp_path)
    pdf.output(output_path)

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
        slices = slice_image(image_path)
        output_pdf_path = os.path.splitext(image_path)[0] + "_sliced.pdf"
        images_to_pdf(slices, output_pdf_path)
        print(f"PDF saved to {output_pdf_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
