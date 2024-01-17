# call with `time python3 copyrightFixer.py /home/ps/Documents/p118/projects/p118-bora.tfs`
# maintainer: mpetrick@data-modul

import os
import argparse

class CopyrightUpdater:
    """
    A class to update copyright lines in source code files.

    Attributes:
        directory (str): The path to the directory where files will be searched and updated.
    """

    def __init__(self, directory):
        """
        Constructs all the necessary attributes for the CopyrightUpdater object.

        Parameters:
            directory (str): The path to the directory where files will be searched and updated.
        """
        self.directory = directory

    def replace_copyright_in_file(self, file_path):
        """
        Replaces the copyright line in a single file.

        Parameters:
            file_path (str): The path to the file to be updated.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                contents = file.readlines()

            modified = False
            for i, line in enumerate(contents):
                if "Copyright (C) 2023 Data Modul AG" in line:
                    contents[i] = line.replace("2023", "2024")
                    modified = True

            if modified:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.writelines(contents)

        except IOError as e:
            print(f"Error processing file {file_path}: {e}")

    def process_directory(self):
        """
        Processes each file in the directory and its subdirectories.
        """
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.endswith(('.h', '.hpp', '.cpp', '.qml', '.lua', '.js')):
                    file_path = os.path.join(root, file)
                    self.replace_copyright_in_file(file_path)

def main():
    """
    The main function to parse command line arguments and initiate the process.
    """
    parser = argparse.ArgumentParser(description='Update copyright lines in code files.')
    parser.add_argument('path', type=str, help='The path to the directory to process')
    args = parser.parse_args()

    updater = CopyrightUpdater(args.path)
    updater.process_directory()

if __name__ == "__main__":
    main()
