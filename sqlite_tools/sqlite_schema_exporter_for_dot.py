import sqlite3
import sys

def get_table_list(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    return [table[0] for table in tables]

def get_table_schema(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()

def sqlite_to_dot(db_path):
    conn = sqlite3.connect(db_path)
    tables = get_table_list(conn)

    dot_schema = 'digraph G {\n'
    for table in tables:
        columns = get_table_schema(conn, table)
        for column in columns:
            dot_schema += f'"{table}" -> "{column[1]}";\n'
    dot_schema += '}'

    return dot_schema

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python sqlite_schema_exporter_for_dot.py <db_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    dot_schema = sqlite_to_dot(db_path)
    with open(db_path.replace('.db', '.dot'), 'w') as f:
        f.write(dot_schema)
