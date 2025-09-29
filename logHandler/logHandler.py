# Write me a Python 3 program which can be used to ingest all the output from stdout and sterr in a unix-like environment (most likely Linux 5-x or 6.x).
# It should take all the input and put it into a file. The file name should be the current date in the format YYYYMMDD-HHSS. If there is already a file with that name, then append to it.
# The program should also check if the content of the file is bigger than 10 MiByte. If so, then create a new file. Also check if there are more than Y files open. The number of Y should be configurable via command line. The maximumum size (given before with 10 MiByte) as well.
# Write the program with proper classes. Also write unit-tests for it. And add proper sphinx-docs for the class and methods. Take care to write code which is fitting to the existing PEP8-standard.
# Add error-handling as well and readable and understandable error messages. Write a short guide of how to use the program as well.
# Put in some effort. This is really important for my career. I am trusting you.

import sys
import os
import time
import argparse
import glob

class FileHandler:
    """
    Handles writing output to files based on the maximum file size.
    """
    def __init__(self, max_size):
        """
        Initializes the FileHandler with the given maximum file size.

        Args:
            max_size (int): Maximum file size in MiBytes.
        """
        self.max_size = max_size * 1024 * 1024  # Convert MiBytes to Bytes
        self.current_file = None
        self.current_file_size = 0

    def get_file_name(self):
        """
        Generates a file name based on the current date and time.

        Returns:
            str: Generated file name.
        """
        return time.strftime("%Y%m%d-%H%M%S") + ".log"

    def write(self, output):
        """
        Writes the given output to the current file.

        Args:
            output (str): Output to write to the file.
        """
        if not self.current_file or self.current_file_size > self.max_size:
            self.open_new_file()
        try:
            self.current_file.write(output)
            self.current_file.flush()
            self.current_file_size += len(output)
        except IOError as e:
            print(f"Error writing to file: {e}", file=sys.stderr)

    def open_new_file(self):
        """
        Closes the current file (if open) and opens a new file for writing.
        """
        if self.current_file:
            self.current_file.close()
        file_name = self.get_file_name()
        try:
            self.current_file = open(file_name, 'a')
            self.current_file_size = os.path.getsize(file_name)
            print(f"Started new file: {file_name}")
        except IOError as e:
            print(f"Error opening file: {e}", file=sys.stderr)

class OutputFileManager:
    """
    Manages the output files based on the maximum file size and the maximum number of remaining files.
    """
    def __init__(self, max_size, max_files):
        """
        Initializes the OutputFileManager with the given maximum file size and maximum number of remaining files.

        Args:
            max_size (int): Maximum file size in MiBytes.
            max_files (int): Maximum number of remaining files.
        """
        self.max_files = max_files
        self.file_handler = FileHandler(max_size)

    def write_output(self, output):
        """
        Writes the given output to the current file and performs cleanup of old files if necessary.

        Args:
            output (str): Output to write to the file.
        """
        self.file_handler.write(output)
        self.cleanup_old_files()

    def cleanup_old_files(self):
        """
        Deletes old log files based on the content of the current directory until only the specified number of files are left.
        """
        log_files = sorted(glob.glob("*.log"))
        while len(log_files) > self.max_files:
            try:
                os.remove(log_files.pop(0))
            except OSError as e:
                print(f"Error deleting file: {e}", file=sys.stderr)

def main():
    """
    Main function that parses command-line arguments, initializes the OutputFileManager, and writes input from stdin to files.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--max_size", type=int, default=10, help="Maximum log size in MiBytes")
    parser.add_argument("--max_files", type=int, default=2, help="Maximum number of remaining files")
    args = parser.parse_args()
    print(f"Maximum log size: {args.max_size} MiBytes")
    print(f"Maximum number of remaining files: {args.max_files}")
    manager = OutputFileManager(args.max_size, args.max_files)
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        manager.write_output(line)

if __name__ == "__main__":
    main()

# working state!
# usage:
#
# (.venv) [mpetrick@marcel-precision3551 logHandler]$ python configurableLoremIpsum.py --rate=10 --line=1024 | python logHandler.py --max_size=1 --max_files=3
# Maximum log size: 1 MiBytes
# Maximum number of remaining files: 3
# Started new file: 20230821-162423.log
# Started new file: 20230821-162433.log
# Started new file: 20230821-162443.log
# Started new file: 20230821-162454.log
# ^CTraceback (most recent call last):

# usual call be like:
# (./your_program 2>&1) | python logHandler.py --max_size=10 --max_files=2
