import textwrap
import sys

def remove_lines_and_format(input_filename, output_filename):
    with open(input_filename, 'r') as f:
        lines = f.readlines()

    # Remove every second line
    lines = lines[::2]

    # Join the remaining lines
    text = ' '.join(lines)

    # Format to line length of max 100 characters with word wrapping
    formatted_text = '\n'.join(textwrap.wrap(text, width=100))

    with open(output_filename, 'w') as f:
        f.write(formatted_text)

def main():
    if len(sys.argv) != 3:
        print("Usage: python transcriptFixer.py input.txt output.txt")
        return

    input_filename = sys.argv[1]
    output_filename = sys.argv[2]

    remove_lines_and_format(input_filename, output_filename)

    print(f"The formatted text has been written to '{output_filename}'.")

if __name__ == "__main__":
    main()

# python transcriptFixer.py input.txt output.txt
