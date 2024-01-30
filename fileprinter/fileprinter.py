import os

class FileExplorer:
    def __init__(self, path):
        self.path = path
        self.file_types = ['.cpp', '.h', '.qrc', '.qml', '.pro']

    def is_target_file(self, filename):
        return any(filename.endswith(ext) for ext in self.file_types)

    def print_file_content(self, file_path):
        try:
            with open(file_path, 'r') as file:
                print("----------\n{}\n----".format(file_path))
                print(file.read())
                print("----------\n")
        except IOError as e:
            print("Error opening file {}: {}".format(file_path, e))

    def explore(self):
        for root, dirs, files in os.walk(self.path):
            for file in files:
                if self.is_target_file(file):
                    full_path = os.path.join(root, file)
                    self.print_file_content(full_path)

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_explore>")
        sys.exit(1)

    path = sys.argv[1]
    explorer = FileExplorer(path)
    explorer.explore()
