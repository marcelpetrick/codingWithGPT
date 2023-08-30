# idea to fix:
# * take current v1.12.7 release
# * import take the current db from TDM
# * import the given ts-files (`source`)
# * export the ts-files (`target`)
# * create program which does the matching from `source` to `target` and fixes the `target`-file
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

def find_unfinished_entries(target_tree):
    """
    Finds all 'unfinished' entries in a .ts file.

    :param target_tree: The ElementTree object of the target .ts file.
    :type target_tree: ET.ElementTree
    :return: A list of 'source' texts of unfinished entries.
    :rtype: list of str
    """
    unfinished_entries = []
    root = target_tree.getroot()

    for message in root.iter('message'):
        translation = message.find('translation')
        if translation is not None and translation.attrib.get('type') == 'unfinished':
            source_text = message.find('source').text
            unfinished_entries.append(source_text)

    return unfinished_entries

def update_translations(target_tree, source_tree, unfinished_entries):
    """
    Updates the translations in the target .ts file with the translations from
    the source .ts file.

    :param target_tree: The ElementTree object of the target .ts file.
    :type target_tree: ET.ElementTree
    :param source_tree: The ElementTree object of the source .ts file.
    :type source_tree: ET.ElementTree
    :param unfinished_entries: A list of 'source' texts of unfinished entries.
    :type unfinished_entries: list of str
    """
    target_root = target_tree.getroot()
    source_root = source_tree.getroot()

    for message in source_root.iter('message'):
        source_text = message.find('source').text
        if source_text in unfinished_entries:
            translation = message.find('translation')
            if translation is not None and translation.attrib.get('type') != 'unfinished':
                translation_text = translation.text
                update_target_translation(target_root, source_text, translation_text)

def update_target_translation(target_root, source_text, translation_text):
    """
    Updates the translation of a specific 'source' text in the target .ts file
    and removes the 'unfinished' attribute.

    :param target_root: The root element of the target .ts file.
    :type target_root: ET.Element
    :param source_text: The 'source' text of the entry to update.
    :type source_text: str
    :param translation_text: The new 'translation' text.
    :type translation_text: str
    """
    for message in target_root.iter('message'):
        if message.find('source').text == source_text:
            translation = message.find('translation')
            translation.text = translation_text
            if 'type' in translation.attrib:
                del translation.attrib['type']

def main():
    """
    The main entry point of the script. It checks if the target and source file paths
    were given as command line arguments and if so, calls the functions to find
    unfinished entries in the target .ts file, update them with the translations from
    the source .ts file, and write the updated target .ts file back to disk.
    """
    if len(sys.argv) < 3:
        print("Usage: python script.py target=targetfile.ts source=source.ts")
        return

    target_file = sys.argv[1].split('=')[1]
    source_file = sys.argv[2].split('=')[1]

    target_tree = ET.parse(target_file)
    source_tree = ET.parse(source_file)

    unfinished_entries = find_unfinished_entries(target_tree)
    update_translations(target_tree, source_tree, unfinished_entries)

    target_tree.write(target_file, encoding='utf-8')


# $ python translationMerger.py target=recipebook_en_GB.ts source=230802_XBO_Automatikprogramme_en_GB-de-en_gb-QA-C.ts
if __name__ == "__main__":
    main()
