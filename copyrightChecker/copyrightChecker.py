import os
import fnmatch
import itertools


def find_files(directory, pattern):
    """
    Yield all the files in the directory that match the pattern.

    :param directory: str, the directory to search.
    :param pattern: str, the pattern to match files against.
    :yield: str, the full path of a matching file.
    """
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename


def check_copyright(directory):
    """
    Check files in the directory for copyright text and print the files that don't contain it.

    :param directory: str, the directory to check.
    :return: list, a list of files that don't contain the copyright text.
    """
    patterns = ['*.h', '*.cpp']
    total_files = 0
    copyrightless_files = 0
    copyright_text = "Copyright (C) 2023 Data Modul AG"
    result_list = []

    for pattern in patterns:
        for filename in find_files(directory, pattern):
            total_files += 1
            try:
                with open(filename, 'r') as f:
                    lines = list(itertools.islice(f, 100))
                    if not any(copyright_text in line for line in lines):
                        result_list.append(filename)
                        copyrightless_files += 1
            except Exception as e:
                print(f"Error reading file {filename}: {str(e)}")

    print(f'Checked {total_files} files. {copyrightless_files} files did not have the copyright line.')
    return result_list


def filter_list(input_list: list, filter_string_list: list):
    """
    Remove all entries from input_list which contain any string from filter_string_list.

    :param input_list: list, the list of strings to filter.
    :param filter_string_list: list, the list of strings to filter out.
    :return: list, the filtered list.
    """
    return [entry for entry in input_list if not any(filter_string in entry for filter_string in filter_string_list)]


#-----------
directory_to_check = '/home/mpetrick/repos/P118_HMI/'
result_list = check_copyright(directory_to_check)
filtered_list = filter_list(result_list, [
                                            '01_Simulator/protobuf',
                                            '/azure/azureiot/',
                                            '/ioboard/Include/IOBoardAccess',
                                            'ioboardsim/io.pb.h',
                                            'common/shared/notifyguard.h',
                                            '04_Templates/template.h',
                                            'tst_azureiothub/azure/umock_c',
                                            'tst_azureiothub/azure/azure_prov_client',
                                            'tst_azureiothub/azure/azure_c_shared_utility/',
                                            'oboardsimulatorserver/io.pb.h'
                                            'tst_journalcontroller/systemd',
                                            'fff.h',
                                            'httplib.h',
                                            'tst_journalcontroller/systemd',
                                            'azure/azure_macro_utils',
                                            'notifyguard.cpp',
                                            '/template.'
                                            'io.pb.h'
                                          ])
# just to check content
uniqueSortedList = sorted(list(set(filtered_list)))
for elem in uniqueSortedList:
    print(elem)
print(len(uniqueSortedList))
