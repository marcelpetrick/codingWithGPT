# A4 Image Slicer to Printable PDF

A Python tool for splitting large or tall images into A4-sized segments with customizable vertical overlap, and exporting them into a multi-page PDF suitable for printing. Ideal for posters, tall infographics, and any visual meant to be physically tiled across standard printer paper.

## 📜 Background

This is a solution to a surprisingly persistent problem that dates back to the 1990s: how to take a tall image and print it across multiple A4 sheets **with proper overlaps** for easy gluing or taping. Despite modern printers and drivers, this functionality remains oddly elusive.

## 🚀 Features

- Converts any image into a set of A4-sized segments.
- Includes configurable overlap between slices.
- Outputs a multi-page PDF ready to print.
- Optionally saves each slice as a JPEG.
- Designed for modern printers (300 DPI assumed).

## 🖼️ Example Use Case

Say you have a vertical artwork or infographic that you want to print and post on a wall. This script splits the image, adds the necessary overlap for assembly, and generates a PDF file ready to send to your printer.

## 📦 Requirements

Install dependencies with pip:

```bash
pip install -r requirements.txt
````

**requirements.txt**:

```
Pillow
fpdf
pytest
```

## 🧑‍💻 Usage

```bash
python main.py your-image.jpg
```

### Optional Features

* To save individual sliced images:

  * Set `save_parts=True` in `slice_image()` (already configured in `main()`)
  * Output goes to the `slices/` directory by default

## ⚙️ Configuration

You can modify the following constants for different behavior:

* `DPI`: Default is 300 for print quality
* `DEFAULT_OVERLAP_PERCENT`: Adjust overlap between A4 slices (default: 5%)

## 📁 Output

* A multi-page PDF saved as `your-image_sliced.pdf`
* (Optional) JPEG files for each A4 slice in `slices/`

## 📌 Notes

* Overlap ensures printed pages can be manually aligned and glued/taped with no missing content.
* A blank white canvas is added behind each slice to match full A4 size.
* Handles final slice adjustment for uneven heights.

## 📄 License

GPLv3

## 🙋 Why?

Because it should've been solved 25 years ago. But here we are.
