# Below is an example Python script (gitStatsOverTime.py) that:
#
#     Takes the path to a Git repository as a command-line argument.
#     Uses the Git command line (with --use-mailmap) to gather commit history.
#     Extracts the date (with day resolution) and committer’s name for each commit.
#     Converts each committer’s name to an acronym: first letter of first name + last letter of last name.
#     Tally commits per day per acronym.
#     Prints the chronological stats in the requested format.
#
#     Note: This script relies on git being installed and on your PATH.
#     If a .mailmap file exists in the repository, using --use-mailmap will unify names/emails accordingly.

import sys
import subprocess
from collections import defaultdict

def get_acronym(name: str) -> str:
    """
    Given a full name (e.g., 'Alice Horn'),
    return the acronym: first letter of first name + last letter of last name.
    Example:
        'Alice Horn' -> 'An'  (A + n)
        'Bob Carter' -> 'Br'  (B + r)
    This function handles names with multiple spaces but assumes at least one.
    """
    return name # disbaled for now - result not fitting: Marcel Petrick MK???

    name_parts = name.strip().split()
    if len(name_parts) == 0:
        return "??"
    first_name = name_parts[0]
    last_name = name_parts[-1]
    # Avoid index errors if the last name is only 1 character
    if len(last_name) == 1:
        # If last name is a single char, just use it
        return first_name[0].upper() + last_name.upper()
    return first_name[0].upper() + last_name[-1].upper()

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} /path/to/repo")
        sys.exit(1)

    repo_path = sys.argv[1]

    # Prepare a dictionary to count commits per day for each acronym
    # Structure: { 'YYYY-MM-DD': { 'ACRONYM': count, ... }, ... }
    daily_commits = defaultdict(lambda: defaultdict(int))

    # Get the git log, using mailmap if available
    #   Format:   %aN (author name, using mailmap),
    #             %ad (author date, in short format: YYYY-MM-DD)
    # The separator is a tab to make it easy to split.
    try:
        git_log_output = subprocess.check_output(
            [
                "git",
                "-C", repo_path,
                "log",
                "--use-mailmap",
                "--pretty=format:%aN\t%ad",
                "--date=short",
            ],
            text=True
        )
    except subprocess.CalledProcessError as e:
        print("Error calling git:", e)
        sys.exit(1)

    for line in git_log_output.splitlines():
        # Each line: "Author Name<TAB>YYYY-MM-DD"
        parts = line.split("\t")
        if len(parts) != 2:
            # skip malformed lines (unlikely in normal usage)
            continue
        author_name, commit_date = parts
        acronym = get_acronym(author_name)
        daily_commits[commit_date][acronym] += 1

    # Sort the days chronologically
    sorted_days = sorted(daily_commits.keys())

    # Print the results in the desired format
    # Example: 2024-12-13: AH 1, BC 2
    for day in sorted_days:
        # For each acronym, show 'ACRONYM count'
        # Sort the acronyms so we have deterministic output
        day_commits_sorted = sorted(daily_commits[day].items())
        day_commit_str = ", ".join(f"{acronym} {count}" for acronym, count in day_commits_sorted)
        print(f"{day}: {day_commit_str}")

if __name__ == "__main__":
    main()
