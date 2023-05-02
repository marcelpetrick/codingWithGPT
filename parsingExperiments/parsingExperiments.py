# Parse the given strings to a dictionary of key-value-pairs.
def process_string_to_dict(input_string):
    # Strip the prefix b'{ and the suffix }'
    stripped_string = input_string[3:-2]

    # Replace \n and \t and " with nothing
    cleaned_string = stripped_string.replace('\\n', '').replace('\\t', '').replace("\"", "")

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

# Just create fitting input for the "parser" coming from a text-file (quotation mark inside string-challenge).
def read_file_to_list(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = [line.rstrip('\n') for line in file]
    return lines

# combined usage as example
def test_run():
    file_path = 'inputFile.txt'
    lines = read_file_to_list(file_path)
    print(lines)
    for line in lines:
        content = process_string_to_dict(line)
        print(content)

# manual call: disable if you just need the methods for external usage
test_run()

# ------------------------------------------------------------------------------------------------------------------

import unittest

class TestStringProcessing(unittest.TestCase):
    def test_process_string_to_dict(self):
        input_string = 'b\'{"key1": "value1",\\n\\t"key2": "value2",\\n\\t"key3": "value3"}\''
        expected_result = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        result = process_string_to_dict(input_string)
        self.assertEqual(result, expected_result)

    def test_read_file_to_list(self):
        # Create a temporary file for testing
        with open('test_input_file.txt', 'w', encoding='utf-8') as file:
            file.write('b\'{"key1": "value1",\\n\\t"key2": "value2",\\n\\t"key3": "value3"}\'\n')
            file.write('b\'{"key4": "value4",\\n\\t"key5": "value5",\\n\\t"key6": "value6"}\'')

        file_path = 'test_input_file.txt'
        expected_result = [
            'b\'{"key1": "value1",\\n\\t"key2": "value2",\\n\\t"key3": "value3"}\'',
            'b\'{"key4": "value4",\\n\\t"key5": "value5",\\n\\t"key6": "value6"}\''
        ]
        result = read_file_to_list(file_path)
        self.assertEqual(result, expected_result)

# automatically run the unit-tests
if __name__ == '__main__':
    unittest.main()
