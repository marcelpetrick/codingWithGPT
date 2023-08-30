# idea to fix:
# * take current v1.12.7 release
# * import take the current db from TDM
# * import the given ts-files (`source`)
# * export the ts-files (`target`)
# * create program which does the matchin from `source` to `target` and fixes the `target`-file
#
#-------------------------------------------
#
# translationMergerForTsFiles: helper-tool needed which can fix all open, unfinished translations with translations coming from some other input-file (not context-bound)

# load target ts-file, then check each "unfinished" string
# for each: find the string in the source-file
# replace it with translation
# save resulting file
#
#-------------------------------------------


import sys
import xml.etree.ElementTree as ET

def find_unfinished_entries(input_file):
    """
    Finds all 'unfinished' entries in a .ts file and prints them to stdout.

    :param input_file: The path to the .ts file to read.
    :type input_file: str
    """
    tree = ET.parse(input_file)
    root = tree.getroot()

    for message in root.iter('message'):
        translation = message.find('translation')
        if translation is not None and translation.attrib.get('type') == 'unfinished':
            source_text = message.find('source').text
            print(source_text)

def main():
    """
    The main entry point of the script. It checks if the input and output file paths
    were given as command line arguments and if so, calls the function to find
    unfinished entries in the input .ts file.
    """
    if len(sys.argv) < 3:
        print("Usage: python script.py input=inputfile.ts output=out.ts")
        return

    input_file = sys.argv[1].split('=')[1]
    output_file = sys.argv[2].split('=')[1]  # output file is not used in this script

    find_unfinished_entries(input_file)

# $ python translationMerger.py input=recipebook_en_GB.ts output=230802_XBO_Automatikprogramme_en_GB-de-en_gb-QA-C.ts
if __name__ == "__main__":
    main()
