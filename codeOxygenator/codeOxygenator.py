import os
import sys
import argparse
from autoDecorator import AutoDecorator  # Make sure AutoDecorator is accessible

def find_files(directory, extensions):
    """Recursively finds files with the given extensions in the directory."""
    matches = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                matches.append(os.path.join(root, file))
    return matches

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Search for files by extension and decorate with Doxygen comments.")
    parser.add_argument("--path", help="Directory path to search in.", type=str)
    parser.add_argument("--type", help="Comma-separated file extensions to search for.", type=str)

    # Parse arguments
    args = parser.parse_args()

    # Validate arguments
    if not args.path or not args.type:
        parser.print_help()
        sys.exit(1)

    # Validate the path
    if not os.path.isdir(args.path):
        print(f"Error: The path '{args.path}' is not a valid directory.")
        sys.exit(1)

    # Parse extensions and ensure they're in the correct format
    extensions = args.type.split(",")
    extensions = [f".{ext.lstrip('.')}" for ext in extensions]  # Ensure leading dot

    # Find matching files
    matching_files = find_files(args.path, extensions)

    # Initialize AutoDecorator
    decorator = AutoDecorator()

    # Decorate each file
    for file_path in matching_files:
        try:
            print(f"Decorating: {file_path}")
            decorator.analyze_and_decorate_file(file_path)
        except Exception as e:  # Consider catching more specific exceptions
            print(f"Failed to decorate {file_path}: {e}")

if __name__ == "__main__":
    main()

# python codeOxygenator.py --path=test/ --type=cpp,h
