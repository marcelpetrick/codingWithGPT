import fnmatch
import itertools
import os


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


def prepend_copyright_to_file(path, copyright_year="2023", company_name="Data Modul AG"):
    try:
        # Get the filename
        filename = os.path.basename(path)

        # Prepare the text to be prepended
        prepend_text = f"""/**
 * @file    {filename}
 * @brief   TODO add text here
 *
 * Copyright (C) {copyright_year} {company_name}
 *
 * {company_name} owns the sole copyright of the software. Under international
 * copyright laws you (1) may not make a copy of this software except for the
 * purposes of maintaining a single archive copy, (2) may not derive works
 * herefrom, (3) may not distribute this work to others. These rights are
 * provided for information clarification, other restrictions of rights may
 * apply as well.
 *
 */
"""

        # Open the file in read mode and read its contents
        with open(path, 'r') as original_file:
            file_contents = original_file.read()

        # Open the file in write mode, write the prepend text and the original file contents
        with open(path, 'w') as modified_file:
            modified_file.write(prepend_text + file_contents)

        print(f"Text prepended to file: {path}")

    except FileNotFoundError:
        print(f"File not found: {path}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def leProgramme():
    directory_to_check = '/home/mpetrick/repos/P118_HMI/'
    result_list = check_copyright(directory_to_check)
    filtered_list = filter_list(result_list, [
                            '/azure/azureiot/',
                            '/ioboard/Include/IOBoardAccess',
                            '01_Simulator/protobuf',
                            '04_Templates/template.cpp',
                            '04_Templates/template.h',
                            'azure/azure_macro_utils',
                            'common/shared/notifyguard.h',
                            'fff.h',
                            'httplib.h',
                            'io.pb.h',
                            'ioboardsim/io.pb.h',
                            'notifyguard.cpp',
                            'oboardsimulatorserver/io.pb.h',
                            'tst_azureiothub/azure/azure_c_shared_utility/',
                            'tst_azureiothub/azure/azure_prov_client',
                            'tst_azureiothub/azure/umock_c',
                            'tst_journalcontroller/systemd',
                                              ])
    # just to check content
    uniqueSortedList = sorted(list(set(filtered_list)))

    for elem in uniqueSortedList:
        print(elem)
    print(f'items: {len(uniqueSortedList)}')

    for file in uniqueSortedList:
        prepend_copyright_to_file(file)


# --------------------------
leProgramme()
