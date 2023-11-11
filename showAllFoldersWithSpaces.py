# GPT4: "good, works now. Don't modify the script, but tell me a proper check with regular expression, which allows only numbers from 0 to 9, underscore and upper- and lower-case latin characters (the usual 26) for the filename. Put this check into a function which returns true or false. name fo the function: noWeirdCharsPlease()."
import re

def noWeirdCharsPlease(filename):
    pattern = r'^[A-Za-z0-9_]+$'
    return bool(re.match(pattern, filename))

# # Example usage
# print(noWeirdCharsPlease("example_filename123"))  # True
# print(noWeirdCharsPlease("example filename123"))  # False


# GPT4: Create me a python script which takes the given path (else use the current one as parameter) and then checks all directories there if they contain a space character in their name. If yes, then collect them in a list. Print this list at last, then return.""

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
        if entry.is_dir() and not noWeirdCharsPlease(entry.name):
            directories_with_space.append(entry.name)

    print("Directories with weird (non \"latin char nor arabic digits or underscore\") in their names:", directories_with_space)
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

# linux
# python showAllFoldersWithSpaces.py /home/mpetrick/repos/DevNotes/BeenThereSeenThat/
#
# (venv) [mpetrick@marcel-precision3551 codingWithGPT]$ python showAllFoldersWithSpaces.py /home/mpetrick/repos/DevNotes/BeenThereSeenThat/
# path_arg: /home/mpetrick/repos/DevNotes/BeenThereSeenThat/
# Directories with weird (non "latin char nor arabic digits or underscore") in their names: ['20231018_Agilität_im_PMO_So_geht_PMO_Aufbau_und_Entwicklung_heute', '20230522_ChatGPT_fuer_HR_Marketing_und_Führungskraefte']
# (venv) [mpetrick@marcel-precision3551 codingWithGPT]$
