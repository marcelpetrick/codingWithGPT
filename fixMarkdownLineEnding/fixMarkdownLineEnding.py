import sys
import os

def add_double_spaces(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    updated_lines = []
    for line in lines:
        stripped_line = line.rstrip()
        if not stripped_line.endswith('  '):
            stripped_line += '  '
        updated_lines.append(stripped_line + '\n')

    with open(file_path, 'w') as file:
        file.writelines(updated_lines)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_markdown_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    add_double_spaces(file_path)
    print(f"Double spaces added to the end of each line in '{file_path}' if needed.")
