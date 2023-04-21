# GPT4: Create me a python script which takes the given path (else use the current one as parameter) and then checks all directories there if they contain a space character in their name. If yes, then collect them in a list. Print this list at last, then return.""

import os
from pathlib import Path

import os
import sys
from pathlib import Path


def check_space_in_directory_names(path=None):
    if path is None:
        path = os.getcwd()
    else:
        path = Path(path)

    directories_with_space = []

    for entry in os.scandir(path):
        if entry.is_dir() and ' ' in entry.name:
            directories_with_space.append(entry.name)

    print("Directories with space in their names:", directories_with_space)
    return directories_with_space

# This needed more specification, but with that additional prompt it incorporated the arg-parsing ..
# GPT4: How to get the first parameter for the python call of the script? with example call for windows

if __name__ == "__main__":
    path_arg = None
    if len(sys.argv) > 1:
        path_arg = sys.argv[1]
    print("path_arg:", path_arg)
    check_space_in_directory_names(path_arg)


#-------------------------------------------

# call:
# PS C:\mpetrick\repos\codingWithGPT> python .\showAllFoldersWithSpaces.py "C:\\mpetrick\\repos\\DevNotes\\BeenThereSeenThat"
# path_arg: C:\\mpetrick\\repos\\DevNotes\\BeenThereSeenThat
# Directories with space in their names: ['20221029_NeuroTechMUC Hackathon_Day0', '20221107_Die MachtDerKoerperspracheImBusiness', '20230412_Which_kernel_for_your_Embedded_Linux project']
# PS C:\mpetrick\repos\codingWithGPT>
