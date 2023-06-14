import re
import sys
import subprocess

def extract_ticket_number(commit_msg):
    # Try to find a ticket number (e.g. #123) in the commit message
    match = re.search(r'#(\d+)', commit_msg)
    # If found, return it, otherwise return an empty string
    return match.group(1) if match else ''

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

def get_commit_info(commit_range):
    # Run 'git log --oneline' command
    result = subprocess.run(['git', 'log', '--oneline', commit_range],
                            text=True, capture_output=True, check=True)

    output_lines = result.stdout.strip().split('\n')
    for line in output_lines:
        commit_hash = line.split()[0]
        commit_msg = subprocess.run(['git', 'log', '--format=%B', '-n', '1', commit_hash],
                                    text=True, capture_output=True, check=True).stdout
        ticket_number = extract_ticket_number(commit_msg)
        if ticket_number:
            print(f'{process_line(line)} ({ticket_number})')
        else:
            print(process_line(line))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} COMMIT_RANGE', file=sys.stderr)
        sys.exit(1)

    get_commit_info(sys.argv[1])

# call from the repo which should be examined like
#
# $ python3 ../repo/gitLogCleaner/gitLogPreparator.py v1.12.0..v1.12.1
# v1.12.1: adapted for the release (12345)
# warning-fix: two different types in the conditional expressions.
# API update v3.14.15 (23456)
# Major new feature (26789)
# Minor feature (18992)
# [..]
