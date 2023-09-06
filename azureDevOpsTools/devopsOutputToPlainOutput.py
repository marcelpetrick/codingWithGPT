import sys
import os
import ast


def parse_file(filename):
    """Parse the input file and convert each line to a dictionary."""
    with open(filename, 'r') as file:
        for line in file:
            yield ast.literal_eval(line.strip())


def format_output(data_dict):
    """Format the dictionary data to the specified output format."""
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


def save_to_file(data, output_filename):
    """Save the formatted data to the specified output file."""
    with open(output_filename, 'w') as file:
        for item in data:
            file.write(item + '\n')


def main():
    # Check if filename is provided
    if len(sys.argv) < 2:
        print("Usage: python devopsOutputToPlainOutput.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]

    # Check if file exists
    if not os.path.exists(filename):
        print(f"Error: The file {filename} does not exist!")
        sys.exit(1)

    try:
        # Parse the file and format the output
        parsed_data = parse_file(filename)
        formatted_data = [format_output(item) for item in parsed_data]

        # Extract the date from the input filename for the output filename
        date_str = filename.split("_")[-1].replace(".txt", "")
        output_filename = f"tickets_plain_output_{date_str}.txt"

        save_to_file(formatted_data, output_filename)
        print(f"Output saved to {output_filename}")

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


# call with:
# $ python devopsOutputToPlainOutput.py tickets_DMO_toImplement_20230906_0959.txt
