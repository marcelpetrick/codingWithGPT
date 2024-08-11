Please write me a Python 3 program that is as Pythonic and failsafe as possible. Additionally, include all the necessary documentation and provide a requirements.txt file.

I want to be able to call the Python script with a directory path as an argument. This directory will contain multiple Markdown files (all ending with .md). The program should:

    Retrieve the list of Markdown files in the directory.
    Sort the files in descending order by their names.
    Take the content of each file and insert it into a new file called concatenated.md. The format should be as follows:
        First, add a line of dashes like "--------------------".
        On a new line, write the name of the file whose content is being inserted.
        Add an empty newline.
        Insert the content of the file.
        Repeat the above steps for each file.

At the end of the process, close all files and report:

    The total number of bytes that have been merged.
    The total number of files that were involved.

Finally, print these details to stdout.
