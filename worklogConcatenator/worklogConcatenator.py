import os
import sys
from pathlib import Path


def merge_markdown_files(directory: str, output_file: str = "concatenated.md") -> None:
    """
    Merges the content of all markdown (.md) files in the given directory into a single file.

    Args:
        directory (str): The path to the directory containing markdown files.
        output_file (str): The name of the output file where the contents will be concatenated.

    Raises:
        FileNotFoundError: If the directory does not exist.
        Exception: For any other exception that might occur during file operations.
    """
    # Validate the directory
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"The directory {directory} does not exist.")

    # Get the list of markdown files and sort them in descending order
    markdown_files = sorted([f for f in os.listdir(directory) if f.endswith('.md')], reverse=True)

    # Initialize counters
    total_bytes = 0
    file_count = 0

    # Open the output file for writing
    try:
        with open(output_file, 'w') as output_fp:
            for file_name in markdown_files:
                file_path = os.path.join(directory, file_name)

                # Read the content of the markdown file
                with open(file_path, 'r') as input_fp:
                    content = input_fp.read()

                # Write to the output file
                output_fp.write("--------------------\n")
                output_fp.write(f"{file_name}\n\n")
                output_fp.write(content + "\n\n")

                # Update counters
                total_bytes += len(content)
                file_count += 1

        # Print the results to stdout
        print(f"Total {file_count} files merged.")
        print(f"Total {total_bytes} bytes written.")

    except Exception as e:
        raise Exception(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python merge_markdown_files.py <directory_path>")
        sys.exit(1)

    directory_path = sys.argv[1]
    try:
        merge_markdown_files(directory_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

# -----------
# $ python worklogConcatenator.py /home/mpetrick/Desktop/dailyLogs_copy/
