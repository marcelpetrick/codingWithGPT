import sys
import fileinput

def add_backslash_to_lines_inplace(input_file):
    try:
        # Use fileinput to modify the input file in place
        with fileinput.FileInput(input_file, inplace=True, backup='.bak') as infile:
            for line in infile:
                # Remove leading/trailing whitespaces and newlines
                line = line.strip()
                # Append a backslash to the end of the line
                line += " \\"
                # Print the modified line to the input file (this will overwrite the original content)
                print(line)
    except FileNotFoundError:
        print(f"Error: File not found: {input_file}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert_with_backslash.py <input_file>")
        sys.exit(1)

    input_file_name = sys.argv[1]
    add_backslash_to_lines_inplace(input_file_name)
    print(f"Conversion successful. Input file '{input_file_name}' modified in place.")

