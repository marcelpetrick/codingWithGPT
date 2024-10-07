import subprocess
import sys
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
    Print the changes in a human-readable format.
    """
    if not changes:
        print("No changes detected.")
        return

    print("File changes summary:")
    for file, change_count in changes.items():
        print(f"{file}: {change_count} changes")

def main():
    # Default parameters
    path = "."
    ncommits = 10

    # Get the list of changes
    changes = get_changes_by_file(path, ncommits)

    # Print the changes
    print_changes(changes)

if __name__ == "__main__":
    main()
