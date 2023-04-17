# I want to find all the files with ending txt which are in a subdirectory called "dataset". Return this as a list.
def find_txt_files(path: str = "dataset") -> list:
    import pathlib
    path_obj = pathlib.Path(path)
    txt_files = list(path_obj.glob("**/*.txt"))
    return [str(file) for file in txt_files]

def testcall_for_find_txt_files():
    txt_files_list = find_txt_files()
    print(txt_files_list)


# I want to read now the content of one file into a 2D matrix. Something which I can index with x,y for easier
# access. You know, for rows and columns. Also add a check for differing line lengths which should result in a
# MalformedInputException. Also check if the input characters are only coming from the set of the two possible
# characters {X, _}. Else throw again a MalformedInputException.
class MalformedInputException(Exception):
    pass

def read_file_to_matrix(file_path: str) -> list:
    matrix = []
    with open(file_path, 'r') as file:
        lines = file.readlines()
        line_length = len(lines[0].strip())

        for line in lines:
            line = line.strip()
            if len(line) != line_length:
                raise MalformedInputException("All lines must have the same length.")

            row = []
            for char in line:
                if char not in {'X', '_'}:
                    raise MalformedInputException("Invalid character encountered. Allowed characters are 'X' and '_'.")

                row.append(char)
            matrix.append(row)

    return matrix

def testcall_for_read_file_to_matrix():
    try:
        txt_files_list = find_txt_files()
        file_path = txt_files_list[0]  # Replace with the desired index or file path
        matrix = read_file_to_matrix(file_path)
        print(matrix)
        # Show me how to access the element 5,10 in the matrix for reading?
        try:
            element = matrix[4][9]  # indices are zero-based, so use 4 and 9 for row 5 and column 10
            print("Element at row 5, column 10:", element)
        except IndexError:
            print("Error: Index out of bounds")

    except MalformedInputException as e:
        print(f"Error: {e}")

testcall_for_read_file_to_matrix()
