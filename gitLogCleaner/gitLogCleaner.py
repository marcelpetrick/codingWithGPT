import sys


def process_line(line):
    # Find first occurrence of ':' character
    index = line.find(':')

    # If ':' exists, remove everything before it
    # Keep the rest of the line as it is
    if index != -1:
        return line[index + 1:].strip()
    else:
        # If there's no ':' character in the line, return the line as it is
        return line.strip()


# Read input from the pipe line by line
for line in sys.stdin:
    print(process_line(line))
