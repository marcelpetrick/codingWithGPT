## What is CRaST?
CRaST (Completely Random Speed Test) is a Python tool for automated internet speed testing. It downloads a specified file at regular intervals and logs the download speed.

## Key Features
- Automatic download of a pre-defined file at 10-second intervals.
- Real-time logging of download speed in Mbps.
- Timestamped output for tracking performance over time.

## Getting Started

### Prerequisites
- Python 3.x
- `requests` Python library

### Installation
1. Ensure Python 3.x is installed on your system.
2. Install the `requests` library:
```bash
pip install -r requirements.txt
```
or via toml:
```bash
pip install poetry
poetry install
```
   
### Configuration
- Modify the url variable in the script to point to the desired file for download speed testing.
- The default file is a 7.7 MB ISO from archive.org.

### Running the Tool
- Open a terminal or command prompt.
- Navigate to the directory containing the script.
- Run the script:
```bash
python CRaST.py
```

### Output
```bash
(venv) [mpetrick@marcel-precision3551 CRaST]$ python CRaST.py 
02:07:58 | File Size: 7.69 MB | Time: 4.75 s | Speed: 12.95 Mbps
02:08:11 | File Size: 7.69 MB | Time: 3.27 s | Speed: 18.81 Mbps
02:08:38 | File Size: 7.69 MB | Time: 17.63 s | Speed: 3.49 Mbps
02:09:16 | File Size: 7.69 MB | Time: 27.25 s | Speed: 2.26 Mbps
02:09:40 | File Size: 7.69 MB | Time: 14.50 s | Speed: 4.24 Mbps
..
```

## Author
Marcel Petrick - mail@marcelpetrick.it
