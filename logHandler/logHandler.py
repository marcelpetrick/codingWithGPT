# Write me a Python 3 program which can be used to ingest all the output from stdout and sterr in a unix-like environment (most likely Linux 5-x or 6.x).
# It should take all the input and put it into a file. The file name should be the current date in the format YYYYMMDD-HHSS. If there is already a file with that name, then append to it.
# The program should also check if the content of the file is bigger than 10 MiByte. If so, then create a new file. Also check if there are more than Y files open. The number of Y should be configureable via command line. The maximumum size (given before with 10 MiByte) as well.
# Write the program with proper classes. Also write unit-tests for it. And add proper sphinx-docs for the class and methods. Take care to write code which is fitting to the existing PEP8-standard.
# Add error-handling as well and readable and understandable error messages. Write a short guide of how to use the program as well.
# Put in some effort. This is really important for my career. I am trusting you.

import sys
import os
import time
import argparse
import glob

class FileHandler:
    def __init__(self, max_size):
        self.max_size = max_size * 1024 * 1024  # Convert MiBytes to Bytes
        self.current_file = None
        self.current_file_size = 0

    def get_file_name(self):
        return time.strftime("%Y%m%d-%H%M%S") + ".log"

    def write(self, output):
        if not self.current_file or self.current_file_size > self.max_size:
            self.open_new_file()
        try:
            self.current_file.write(output)
            self.current_file.flush()
            self.current_file_size += len(output)
        except IOError as e:
            print(f"Error writing to file: {e}", file=sys.stderr)

    def open_new_file(self):
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
    def __init__(self, max_size, max_files):
        self.max_files = max_files
        self.file_handler = FileHandler(max_size)
        self.open_files = []

    def write_output(self, output):
        self.check_open_files()
        self.file_handler.write(output)
        if self.file_handler.current_file not in self.open_files:
            self.open_files.append(self.file_handler.current_file)

    def check_open_files(self):
        while len(self.open_files) >= self.max_files:
            try:
                file_to_close = self.open_files.pop(0)
                file_to_close.close()
                os.remove(file_to_close.name)
            except IOError as e:
                print(f"Error closing file: {e}", file=sys.stderr)

def main():
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
