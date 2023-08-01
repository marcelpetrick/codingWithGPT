import sqlite3
import os
import argparse

def export_images(db_name):
    # Connect to the sqlite database
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Select the columns
    cursor.execute("SELECT fallback_name, background_image FROM bora_recipe")

    # Fetch all rows from the query
    data = cursor.fetchall()

    print(f"Fetched {len(data)} rows from the database.")

    # If the data directory doesn't exist, create it
    if not os.path.exists('images'):
        os.mkdir('images')

    # Loop through the rows and save each image
    for i, row in enumerate(data):
        name, image = row
        image_path = os.path.join('images', f"{name}.png")

        print(f"Processing row {i + 1} / {len(data)}: Saving image as {image_path}")

        # Write the image data to a file
        try:
            with open(image_path, 'wb') as file:
                file.write(image)
        except Exception as e:
            print(f"Failed to write image: {e}")

        print(f"Successfully saved image as {image_path}")

    print("Finished exporting images.")

    # Close the connection
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export images from a SQLite database.")
    parser.add_argument("dbname", help="The name of the SQLite database")

    args = parser.parse_args()

    export_images(args.dbname)
