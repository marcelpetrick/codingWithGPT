# i have a sqlite3 database. i want to dump all the data into a textfile. so i need all text and json fields, but nothing which is a BLOB from inside the database and tables.
# write me a python3 script, which can load the database (path coming as argument from the call like `python sqlite3dumper.py in=database.sqlite out=outfile.txt. If "out" is not set, then print to stdout.
#
# so then open the database and put all data in a strxutured way to the textfile. add error handling and readable error messages. make the code object oriented and based on at least one class.

import sqlite3
import sys


class SQLite3Dumper:

    def __init__(self, db_path, output=None):
        self.db_path = db_path
        self.output = output

    def get_column_names(self, table_name):
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        columns_info = cur.fetchall()
        con.close()
        return [col[1] for col in columns_info]

    def dump_data(self):
        table_name = "bora_recipe"
        all_columns = self.get_column_names(table_name)

        # Exclude the specified columns
        selected_columns = [col for col in all_columns if col not in ["icon", "background_image", "steps_json", "develop_flag", "qr_image", "menu_flag", "subcategory", "url"]]

        con = sqlite3.connect(self.db_path)
        cur = con.cursor()

        dump_string = f"Table: {table_name}\n"
        dump_string += ", ".join(selected_columns) + "\n"
        dump_string += "-" * len(", ".join(selected_columns)) + "\n"

        cur.execute(f"SELECT {', '.join(selected_columns)} FROM {table_name}")
        rows = cur.fetchall()
        for row in rows:
            dump_string += ", ".join([str(item) for item in row]) + "\n"

        con.close()

        if self.output:
            with open(self.output, 'w') as f:
                f.write(dump_string)
        else:
            print(dump_string)


if __name__ == '__main__':
    args = {}
    for arg in sys.argv[1:]:
        key, value = arg.split('=')
        args[key] = value

    try:
        if 'in' not in args:
            raise ValueError('Database path not specified. Use "in" to specify the path.')

        output = args.get('out')
        dumper = SQLite3Dumper(args['in'], output)
        dumper.dump_data()

    except Exception as e:
        print(f"Error: {e}")

# usage:
# $ python sqlite3dumper.py in=recipebook.sqlite

# dump with bash:
# $ sqlite3 recipebook.sqlite  .dump > dump.sql.txt

