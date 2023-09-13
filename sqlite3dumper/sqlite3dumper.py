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

    def get_table_names(self):
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        con.close()
        return [table[0] for table in tables]

    def dump_data(self):
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()

        table_names = self.get_table_names()

        dump_string = ""
        for table in table_names:
            dump_string += f"Table: {table}\n"

            cur.execute(f"PRAGMA table_info({table})")
            columns_info = cur.fetchall()
            text_and_json_columns = [col[1] for col in columns_info if col[2] in ["TEXT", "JSON"]]

            if text_and_json_columns:
                # Add column headers
                dump_string += ", ".join(text_and_json_columns) + "\n"
                dump_string += "-" * len(", ".join(text_and_json_columns)) + "\n"

                cur.execute(f"SELECT {', '.join(text_and_json_columns)} FROM {table}")
                rows = cur.fetchall()
                for row in rows:
                    dump_string += ", ".join([str(item) for item in row]) + "\n"
            dump_string += "\n"

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

