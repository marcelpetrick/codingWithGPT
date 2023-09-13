#!/bin/bash

DB_PATH="$1"
OUTPUT_PATH="$2"

# Dump the schema first
sqlite3 "$DB_PATH" .schema > "$OUTPUT_PATH"

# Loop through each table and export the TEXT columns
TABLES=$(sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table';")

for TABLE in $TABLES; do
    TEXT_COLUMNS=$(sqlite3 "$DB_PATH" "PRAGMA table_info($TABLE);" | awk -F'|' '{if ($3 == "TEXT") print $2}' | tr '\n' ',' | sed 's/,$//')

    if [ ! -z "$TEXT_COLUMNS" ]; then
        echo -e "\n-- Data for table $TABLE" >> "$OUTPUT_PATH"
        sqlite3 "$DB_PATH" "SELECT $TEXT_COLUMNS FROM $TABLE;" >> "$OUTPUT_PATH"
    fi
done
