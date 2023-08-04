import os
import fnmatch


def find_files(directory, pattern):
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename


def check_copyright(directory):
    patterns = ['*.h', '*.cpp']
    total_files = 0
    copyrightless_files = 0
    copyright_text = "Copyright (C) 2023 Data Modul AG"

    for pattern in patterns:
        for filename in find_files(directory, pattern):
            total_files += 1
            with open(filename, 'r') as f:
                lines = [next(f) for _ in range(100)]
                if copyright_text not in lines:
                    print(filename)
                    copyrightless_files += 1

    print(f'Checked {total_files} files. {copyrightless_files} files did not have the copyright line.')


directory_to_check = '/home/mpetrick/repos/P118_HMI/'
check_copyright(directory_to_check)
