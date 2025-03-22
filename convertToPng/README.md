# convertToPng

A simple Python 3 script that scans the current directory for image files (`jpg`, `jpeg`, `webp`, `wbp`, `png`), converts them to PNG (if they aren't already), and saves them in a `png/` subfolder.

## Features

- Converts common image formats (JPG, JPEG, WEBP, WBP) to PNG.
- Copies already existing PNGs without modification.
- Saves all PNG images into a `png/` subdirectory.
- Maintains highest quality by converting images to RGBA and optimizing the PNG output.
- Modular, Pythonic code structure.
- Unit-testable with `unittest` and `pytest`.

## Requirements

- Python 3.12+
- [Pillow](https://python-pillow.org) (Python Imaging Library)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the script in the directory where your images are located:

```bash
python convertToPng
```

Converted/copy PNGs will be saved to the `png/` subfolder (created if it doesn't exist).

## Project Structure

```
LI_vibecoding/
├── convertToPng.py   # Main image processing script
├── test_convertToPng.py # Unit tests
├── requirements.txt     # Dependencies
└── README.md            # Project documentation
```

## Running Tests

Unit tests are written using Python's `unittest` module. To run the tests:

```bash
python test_convertToPng.py
```

You should see output confirming the successful tests, e.g.

```
INFO:convertToPng:Converted ...
INFO:convertToPng:Processing complete!
.
----------------------------------------------------------------------
Ran 5 tests in 0.01s

OK
```

## Future Ideas / Improvements

- Add support for recursive directory traversal.
- Allow user to specify custom output directories.
- Add CLI options (e.g., `argparse`) for better flexibility.
- Implement logging levels via CLI flags.
