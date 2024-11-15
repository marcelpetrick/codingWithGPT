import subprocess
import sys
import argparse
from collections import defaultdict
from pathlib import Path

def get_git_log(path=".", ncommits=20):
    """
    Get the last ncommits and the files changed in them.
    """
    # Run the git log to get the files affected in the last `ncommits`
    try:
        git_log_cmd = ['git', '-C', path, 'log', f'-{ncommits}', '--name-only', '--pretty=format:']
        result = subprocess.run(git_log_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        output = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running git log: {e.stderr}", file=sys.stderr)
        return {}

    return output.splitlines()


def get_changes_by_file(path=".", ncommits=20):
    """
    Get the number of changes per file for the last ncommits.
    """
    # Initialize a defaultdict to store the number of changes per file
    file_changes = defaultdict(int)

    # Get the list of files changed in the last ncommits
    changed_files = get_git_log(path, ncommits)

    # Iterate through the list of changed files and increment their count
    for file in changed_files:
        if file.strip():  # Ignore empty lines
            file_changes[file] += 1

    return file_changes


def calculate_cognitive_complexity(file_path: str) -> int:
    """
    Calculate cognitive complexity of the given file.
    :param file_path: Path to the file
    :return: Cognitive complexity value
    """
    complexity = 0
    nesting_level = 0

    try:
        with open(file_path, "r") as file:
            for line in file:
                stripped_line = line.strip()
                # Increase complexity for control flow structures
                if any(keyword in stripped_line for keyword in ("if", "for", "while", "else", "elif", "switch", "case")):
                    complexity += 1 + nesting_level
                # Handle nesting level
                if "{" in stripped_line or stripped_line.endswith(":"):
                    nesting_level += 1
                if "}" in stripped_line:
                    nesting_level = max(nesting_level - 1, 0)
    except Exception as e:
        print(f"Warning: Could not read {file_path} for cognitive complexity: {e}", file=sys.stderr)
        return 0

    return complexity


def calculate_qml_complexity(file_path: str) -> int:
    """
    Calculate cognitive complexity of the given QML file.
    :param file_path: Path to the file
    :return: Cognitive complexity value
    """
    complexity = 0
    nesting_level = 0

    try:
        with open(file_path, "r") as file:
            for line in file:
                stripped_line = line.strip()
                # Increase complexity for QML elements
                if any(keyword in stripped_line for keyword in ("Rectangle", "Button", "Text", "ListView", "Column", "Row")):
                    complexity += 1 + nesting_level
                # Count property bindings and signals
                if ":" in stripped_line and not stripped_line.endswith("{"):
                    complexity += 1
                if "on" in stripped_line and stripped_line.endswith(":"):
                    complexity += 2  # Handlers are slightly more complex
                # Handle nesting level
                if stripped_line.endswith("{"):
                    nesting_level += 1
                if stripped_line == "}":
                    nesting_level = max(nesting_level - 1, 0)
    except Exception as e:
        print(f"Warning: Could not read {file_path} for QML complexity: {e}", file=sys.stderr)
        return 0

    return complexity


def print_changes(changes, path=".", rate_qml_differently=False):
    """
    Print the changes in a human-readable format, sorted by the number of changes (most to least).
    """
    if not changes:
        print("No changes detected.")
        return

    # Sort the changes by the number of changes in descending order
    sorted_changes = sorted(changes.items(), key=lambda item: item[1], reverse=False)

    print("File changes summary (sorted by most changes):")
    for file, change_count in sorted_changes:
        if rate_qml_differently and file.endswith(".qml"):
            complexity = calculate_qml_complexity(str(Path(path) / file))
        else:
            complexity = calculate_cognitive_complexity(str(Path(path) / file))
        print(f"{file}: {change_count} changes, Cognitive Complexity: {complexity}")


def parse_arguments():
    """
    Parse command line arguments for path, ncommits, and rate_qml_differently.
    """
    parser = argparse.ArgumentParser(
        description="Script to check the number of file changes in the last N git commits."
    )
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Path to the git directory (default is current directory)."
    )
    parser.add_argument(
        "--ncommits",
        type=int,
        default=20,
        help="Number of last commits to check (default is 20)."
    )
    parser.add_argument(
        "--rateQmlDifferently",
        action='store_true',
        help="If set, use a different complexity metric for QML files."
    )

    return parser.parse_args()


def main():
    # Parse command line arguments
    args = parse_arguments()

    # Get the list of changes
    changes = get_changes_by_file(args.path, args.ncommits)

    # Print the changes
    print_changes(changes, args.path, args.rateQmlDifferently)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # If no arguments are provided, show usage information
        print("Usage: python3 script_name.py --path=<path_to_git_repo> --ncommits=<number_of_commits> [--rateQmlDifferently]")
        print("Example: python3 script_name.py --path=/home/user/myrepo --ncommits=10 --rateQmlDifferently")
    else:
        main()
