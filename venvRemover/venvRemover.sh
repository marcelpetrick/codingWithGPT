#!/bin/zsh

# Use first argument as path, or default to current dir
search_path="${1:-.}"

# Expand to full path
search_path=$(realpath "$search_path")

echo "Searching for .venv directories under: $search_path"

# Find all .venv directories
venvs=($(find "$search_path" -type d -name .venv))

if [[ ${#venvs[@]} -eq 0 ]]; then
  echo "No .venv directories found."
  exit 0
fi

echo "\nFound the following .venv directories with their sizes:"
total_size=0

for venv in "${venvs[@]}"; do
  size=$(du -sh "$venv" | cut -f1)
  bytes=$(du -sb "$venv" | cut -f1)
  total_size=$((total_size + bytes))
  echo "$size  $venv"
done

# Convert total size to human-readable
total_hr=$(numfmt --to=iec <<< "$total_size")
echo "\nTotal size to be deleted: $total_hr"

# Prompt user
echo -n "\nDo you want to delete all of them? [y/N]: "
read answer

if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
  for venv in "${venvs[@]}"; do
    rm -rf "$venv"
    echo "Deleted: $venv"
  done
  echo "\nAll .venv directories deleted."
else
  echo "\nAborted. No directories were deleted."
fi
