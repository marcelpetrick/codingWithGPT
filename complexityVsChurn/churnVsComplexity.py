import subprocess
import sys
import argparse
from collections import defaultdict


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


def print_changes(changes):
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
        print(f"{file}: {change_count} changes")


def parse_arguments():
    """
    Parse command line arguments for path and ncommits.
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

    return parser.parse_args()


def main():
    # Parse command line arguments
    args = parse_arguments()

    # Get the list of changes
    changes = get_changes_by_file(args.path, args.ncommits)

    # Print the changes
    print_changes(changes)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # If no arguments are provided, show usage information
        print("Usage: python3 script_name.py --path=<path_to_git_repo> --ncommits=<number_of_commits>")
        print("Example: python3 script_name.py --path=/home/user/myrepo --ncommits=10")
    else:
        main()
