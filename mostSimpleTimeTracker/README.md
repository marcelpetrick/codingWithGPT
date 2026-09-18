# Simple Time Tracking Tool

A lightweight and flexible time tracking tool built using Python and PyQt5. It features a minimal user interface and allows tracking time spent on tasks with ease. Each second is logged, and a summary of the time spent on each task is displayed.

## Features

- Simple and minimalistic UI
- Add tasks via a single input field
- Track time in real-time for selected tasks
- Log task durations per day into text files
- Automatically create and update logs
- Summarize time spent on each task in a human-readable format (hours, minutes, and seconds)
- Preserve task names containing colons and mixed-case characters between sessions

## Installation

To run the project, you'll need to have Python and the required dependencies installed.

1. Install the dependencies:

    ```bash
    python -m pip install -r requirements.txt
    ```

2. Run the application:

    ```bash
    python mostSimpeTimeTracker.py
    ```

## Requirements

- Python 3.8 or later
- PyQt5 5.15.11

## Configuration

The task list and current selection are saved to `config.ini` when the application closes and
restored on the next start. Task names may contain colons (`:`), and their original casing is
preserved.

## License

This project is licensed under the GPL-3.0 License.

## Author

Created by Marcel Petrick. For any questions, contact mail@marcelpetrick.it.
