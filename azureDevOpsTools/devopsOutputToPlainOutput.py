import sys
import os
import ast
from typing import Generator, Dict, List


def parse_file(filename: str) -> Generator[Dict[str, str], None, None]:
    """
    Parse the input file and convert each line to a dictionary.

    :param filename: Path to the input file.
    :return: A generator that yields dictionaries from each line of the file.
    """
    with open(filename, 'r') as file:
        for line in file:
            yield ast.literal_eval(line.strip())


def format_output(data_dict: Dict[str, str]) -> str:
    """
    Format the dictionary data to the specified output format.

    :param data_dict: Dictionary containing ticket data.
    :return: Formatted string of ticket data.
    """
    title = data_dict['Title']
    url = data_dict['URL']
    resolved_date = data_dict['Resolved Date']
    closed_date = data_dict['Closed Date']

    if resolved_date is None:
        resolved_date = closed_date if closed_date is not None else 'NONE'

    # List of elements to format
    elements = [title, url, resolved_date]

    # Check for semicolons and replace, then print message
    for idx, element in enumerate(elements):
        if ';' in element:
            elements[idx] = element.replace(';', ',')
            print(f"Replaced ';' with ',' in: {element}")

    return f'{elements[0]}; {elements[1]}; {elements[2]}'


def save_to_file(data: List[str], output_filename: str) -> None:
    """
    Save the formatted data to the specified output file.

    :param data: List of formatted ticket data.
    :param output_filename: Name of the output file.
    """
    with open(output_filename, 'w') as file:
        for item in data:
            file.write(item + '\n')


def main() -> None:
    """Main function to execute the script."""
    if len(sys.argv) < 2:
        print("Usage: python devopsOutputToPlainOutput.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]

    if not os.path.exists(filename):
        print(f"Error: The file {filename} does not exist!")
        sys.exit(1)

    try:
        parsed_data = list(parse_file(filename))
        formatted_data = [format_output(item) for item in parsed_data]

        date_str = filename.split("_")[-1].replace(".txt", "")
        output_filename = f"tickets_plain_output_{date_str}.txt"

        save_to_file(formatted_data, output_filename)
        print(f"Output saved to {output_filename}")

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
