import os
import sys

def check_copyright(file_path):
    with open(file_path, 'r') as file:
        # read the first 20 lines
        for _ in range(20):
            line = file.readline().strip()
            if line == "Copyright (C) 2023":
                return True
    return False

def find_files(directory, extension):
    for dirpath, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(extension):
                file_path = os.path.abspath(os.path.join(dirpath, filename))
                if not check_copyright(file_path):
                    print("missing: " + file_path)

def main():
    # check if path was provided
    if len(sys.argv) != 2:
        print("Please provide the directory path as an argument")
        sys.exit(1)

    directory = sys.argv[1]  # get directory path from arguments
    extensions = ['.cpp', '.h']
    for extension in extensions:
        find_files(directory, extension)

if __name__ == "__main__":
    main()
