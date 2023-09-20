# usage:
#
# $ python findAndFixUpperCaseDirectoryNames.py
# upper-case directories:
# HttpRequestSenderAndReceiverTest
# MotherOfAllGits
# QTestSummer
# SeasonalDecomposition
# HTML_filePickerLineEditTest
# $ python findAndFixUpperCaseDirectoryNames.py --fix
# Renamed directories to lowercase.
# $ 

import os
import sys

def find_uppercase_directories(path="."):
    """Find directories in the given path that start with an uppercase letter."""
    return [d for d in os.listdir(path) if os.path.isdir(d) and d[0].isupper()]

def rename_to_lowercase(directories):
    """Rename the provided directories to lowercase."""
    for directory in directories:
        os.rename(directory, directory.lower())

def main():
    upper_case_directories = find_uppercase_directories()

    if not upper_case_directories:
        print("No upper-case directories found.")
        return

    if "--fix" in sys.argv:
        rename_to_lowercase(upper_case_directories)
        print("Renamed directories to lowercase.")
    else:
        print("upper-case directories:")
        for directory in upper_case_directories:
            print(directory)

if __name__ == "__main__":
    main()
