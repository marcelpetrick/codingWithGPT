import sqlite3
import os
import argparse


def get_table_list(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    return [table[0] for table in tables]


def get_table_schema(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()


def sqlite_to_dot(db_name):
    # Connect to the sqlite database
    conn = sqlite3.connect(db_name)
    tables = get_table_list(conn)

    dot_schema = 'digraph G {\n'
    for table in tables:
        columns = get_table_schema(conn, table)
        for column in columns:
            dot_schema += f'"{table}" -> "{column[1]}";\n'
    dot_schema += '}'

    return dot_schema


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate DOT schema from a SQLite database.")
    parser.add_argument("dbname", help="The name of the SQLite database")

    args = parser.parse_args()

    dot_schema = sqlite_to_dot(args.dbname)
    dot_path = args.dbname.rsplit('.', 1)[0] + '.dot'

    with open(dot_path, 'w') as f:
        f.write(dot_schema)

    print(f"Successfully wrote DOT schema to {dot_path}")
