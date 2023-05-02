def process_string_to_dict(input_string):
    # Strip the prefix b'{ and the suffix }'
    stripped_string = input_string[2:-1]

    # Replace \n and \t with nothing
    cleaned_string = stripped_string.replace('\\n', '').replace('\\t', '')

    # Split the string into key-value pairs
    items = cleaned_string.split(',')

    # Create a dictionary from the key-value pairs
    result_dict = {}
    for item in items:
        key, value = item.split(':', 1)
        # Remove surrounding quotes from the key
        key = key.strip().strip('"')
        result_dict[key] = value.strip()

    return result_dict

def read_file_to_list(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = [line.rstrip('\n') for line in file]
    return lines

# Example usage:
def test_run():
    file_path = 'inputFile.txt'
    lines = read_file_to_list(file_path)
    print(lines)
    for line in lines:
        content = process_string_to_dict(line)
        print(content)

test_run()
