# pip install ezodf
# pip install lxml

import sys
import ezodf

def extract_data_from_column(doc, column_name="C"):
    """
    Extract data from a specific column in the ODS file.

    :param doc: ODS document loaded using ezodf.
    :param column_name: Name of the column to extract data from. Default is 'C'.
    :return: List containing data from the specified column.
    """
    sheet = doc.sheets[0]  # Assuming you want the first sheet
    col_idx = ord(column_name) - ord('A')
    data = []

    for row in sheet.rows():
        try:
            cell = row[col_idx]
            if cell.value_type:
                data.append(cell.value)
        except IndexError:
            continue

    return data

def main():
    # Check if filename is provided
    if len(sys.argv) < 2:
        print("Usage: python getUrlsFromChart.py <filename.ods>")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        # Load the ODS document
        doc = ezodf.opendoc(filename)

        # Extract data from column G
        data = extract_data_from_column(doc, column_name="C")

        # Print the data to stdout
        for item in data:
            print(item)

    except FileNotFoundError:
        print(f"Error: The file {filename} was not found.")
        sys.exit(1)
    except ezodf.PackagedDocumentError:
        print(f"Error: Failed to read the ODS file {filename}. Ensure it's a valid ODS file.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
