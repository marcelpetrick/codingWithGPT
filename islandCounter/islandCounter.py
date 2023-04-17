# "I want to find all the files with ending txt which are in a subdirectory called "dataset". Return this as a list."
def find_txt_files(path: str = "dataset") -> list:
    import pathlib
    path_obj = pathlib.Path(path)
    txt_files = list(path_obj.glob("**/*.txt"))
    return [str(file) for file in txt_files]

def testcall_for_find_txt_files():
    txt_files_list = find_txt_files()
    print(txt_files_list)

# "I want to read now the content of one file into a 2D matrix. Something which I can index with x,y for easier
# access. You know, for rows and columns. Also add a check for differing line lengths which should result in a
# MalformedInputException. Also check if the input characters are only coming from the set of the two possible
# characters {X, _}. Else throw again a MalformedInputException."
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

#testcall_for_read_file_to_matrix()

# "Write me code which prints the matrix in a 2D form to the console."
def print_matrix(matrix: list) -> None:
    for row in matrix:
        print(" ".join(row))
# my call for all the combined functionality
#print_matrix(read_file_to_matrix(find_txt_files()[0]))

# "write me a function which can count the amount of islands in a matrix. The island is marked by all connected
# fields with character X. Check the 8-neighbourhood of each cell. Respect the borders which means no mirroring or
# whatever at the border. Cells with _ mean water. So each island is surrounded either by water or border cells."
def count_islands(matrix: list) -> int:
    def dfs(matrix: list, visited: list, row: int, col: int) -> None:
        rows = len(matrix)
        cols = len(matrix[0])
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

        visited[row][col] = True

        for dr, dc in directions:
            new_row = row + dr
            new_col = col + dc

            if 0 <= new_row < rows and 0 <= new_col < cols and not visited[new_row][new_col] and matrix[new_row][new_col] == 'X':
                dfs(matrix, visited, new_row, new_col)

    rows = len(matrix)
    cols = len(matrix[0])
    visited = [[False] * cols for _ in range(rows)]

    island_count = 0
    for row in range(rows):
        for col in range(cols):
            if not visited[row][col] and matrix[row][col] == 'X':
                island_count += 1
                dfs(matrix, visited, row, col)

    return island_count

def testcall_for_count_islands():
    matrix = read_file_to_matrix(find_txt_files()[0])
    island_count = count_islands(matrix)
    print("Number of islands:", island_count)

#testcall_for_count_islands()

# "write me unit test code for the method count_islands which runs for all the result files from the function find_txt_files."
import unittest

class TestCountIslands(unittest.TestCase):
    def test_count_islands(self):
        expected_island_count = 1 # added by me: since I created the testcases that the first file has 1, the second 2, .. the checks are obvious
        # Iterate through the text files
        for file_path in find_txt_files(): # needed adjustment with the real function
            print("checking now file:", file_path)
            # Read the file into a matrix
            matrix = read_file_to_matrix(file_path)

            # Call the count_islands function
            island_count = count_islands(matrix)

            # Add your test assertions here, e.g., comparing the island_count
            # with the expected result for each file (you should provide the expected results)
            # self.assertEqual(island_count, expected_island_count)
            self.assertEqual(island_count, expected_island_count)
            expected_island_count += 1

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
