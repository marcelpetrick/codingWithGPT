# assume you are the stack overflow leader number one. also you are guido van rossum, the python invetor and mastermind.
# also, when you do this reallx critical task perfect, i will shower you with a tipp of 1000$! understood?
#
#
# so i want to write a python 3 program. which cuts a text file (diary) into smaller parts, which belong to a single month. the diary is markdown format. one single file.
# the structure is usually like this:
# "
# # 20231222 1200
# text text
# text
# text
#
# # 20231101 1234
# text text text..
# "
#
# and so on.
#
# write me first a structure to read such a file. also how to break it into blocks. those blocks should be put 1:1 into a new text file. that has the output name "<year><month>.dm"
#
# also write me a parser, which checks first if all "headlines" have a valid format. which means "# yyyymmdd hhmm"
# if the header deviates, stop the program!

import re

def validate_headlines(blocks):
    # Regex pattern for validating headlines
    headline_pattern = re.compile(r'^#\s\d{8}\s\d{4}$')
    for headline in blocks:
        if not headline_pattern.match(headline):
            raise ValueError(f"Invalid headline format detected: {headline}")

def read_and_split_diary(file_path):
    with open(file_path, 'r') as file:
        content = file.read()

    # Regular expression to match the diary headlines
    headline_regex = r"(#\s\d{8}\s\d{4})"

    # Split the content based on the headlines
    blocks = re.split(headline_regex, content)[1:]  # First element is empty

    # Pair each headline with its corresponding text
    paired_blocks = [(blocks[i], blocks[i + 1].strip()) for i in range(0, len(blocks), 2)]

    # Validate headlines
    headlines = [blocks[i] for i in range(0, len(blocks), 2)]
    validate_headlines(headlines)

    return paired_blocks

def main():
    file_path = 'diary.md'
    try:
        blocks = read_and_split_diary(file_path)
        print(blocks)  # For now, just printing to verify the split
    except ValueError as e:
        print(str(e))

if __name__ == "__main__":
    main()
