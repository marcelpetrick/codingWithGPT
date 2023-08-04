import os
import fnmatch
import itertools


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
    result_list = []

    for pattern in patterns:
        for filename in find_files(directory, pattern):
            total_files += 1
            with open(filename, 'r') as f:
                lines = list(itertools.islice(f, 100))
                foundCopyright = False
                for line in lines:
                    if copyright_text in line:
                        foundCopyright = True
                if not foundCopyright:
                    print(filename)
                    result_list.append(filename)
                    copyrightless_files += 1

    print(f'Checked {total_files} files. {copyrightless_files} files did not have the copyright line.')
    return result_list


def filter_list(input_list : list, filter_string_list : list):
    # remove all entries from result_list which have a certain string
    filtered_list = []
    for entry in input_list:
        found = False
        for filter_string in filter_string_list:
            if filter_string in entry:
                found = True
                break
        if not found:
            filtered_list.append(entry)
    return filtered_list


directory_to_check = '/home/mpetrick/repos/P118_HMI/'
result_list = check_copyright(directory_to_check)
filtered_list = filter_list(result_list, ['protobuf/Target', 'azure_c_shared_utility', 'umock_c', 'azure_prov_client'])
print(len(filtered_list))
print(filtered_list)