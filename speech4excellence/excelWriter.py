import openpyxl
from openpyxl.utils import get_column_letter

class ExcelWriter:
    def __init__(self, filename):
        """
        Initializes the ExcelWriter with a filename.
        Tries to load the workbook if it exists, otherwise creates a new workbook.
        """
        self.filename = filename
        try:
            self.workbook = openpyxl.load_workbook(filename)
        except FileNotFoundError:
            self.workbook = openpyxl.Workbook()

        self.sheet = self.workbook.active

    def insert_pairs(self, pairs):
        """
        Takes a list of string pairs (artist, title) and inserts them into the Excel sheet.
        Each pair goes into a new row, starting from the first row.
        """
        row = 1
        for artist, title in pairs:
            artist_cell = 'A' + str(row)
            title_cell = 'B' + str(row)
            self.sheet[artist_cell] = artist
            self.sheet[title_cell] = title
            row += 1  # Move to the next row

        self.workbook.save(self.filename)

def bundle_as_pairs(input_list):
    """
    Bundles a list of strings into pairs. Assumes the list length is even.
    If the list length is odd, the last element is ignored.
    """
    return [(input_list[i], input_list[i + 1]) for i in range(0, len(input_list) - 1, 2)]

# Example usage:
if __name__ == "__main__":
    input_list = ['Artist1', 'Title1', 'Artist2', 'Title2', 'Artist3', 'Title3']
    pairs = bundle_as_pairs(input_list)
    excel_writer = ExcelWriter('example.xlsx')
    excel_writer.insert_pairs(pairs)