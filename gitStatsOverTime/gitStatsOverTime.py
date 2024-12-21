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
    return the acronym: first letter of the first name + first letter of the last name.

    Example:
        'Alice Horn' -> 'AH'
        'Bob Carter' -> 'BC'

    This function handles names with multiple spaces but assumes at least one.
    """
    name_parts = name.strip().split()
    if not name_parts:
        return "??"  # Return a fallback if no name is given

    first_name = name_parts[0]
    last_name = name_parts[-1]

    return first_name[0].upper() + last_name[0].upper()

def usage_and_exit():
    print(f"Usage: {sys.argv[0]} /path/to/repo [--month]")
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        usage_and_exit()

    # Check if --month is given
    monthly_mode = False
    if '--month' in sys.argv:
        monthly_mode = True
        # Remove it so the remaining arguments make sense
        sys.argv.remove('--month')

    # After removing --month if present, we expect exactly 2 arguments: script and repo path
    if len(sys.argv) != 2:
        usage_and_exit()

    repo_path = sys.argv[1]

    # Data structure to collect commits by day (or month)
    # Structure: { dateKey: { 'ACRONYM': count, ... }, ... }
    # where dateKey is either 'YYYY-MM-DD' or 'YYYY-MM' (if --month is used)
    daily_commits = defaultdict(lambda: defaultdict(int))

    # Gather git log data
    try:
        git_log_output = subprocess.check_output(
            [
                "git",
                "-C", repo_path,
                "log",
                "--use-mailmap",            # respects .mailmap
                "--pretty=format:%aN\t%ad", # Author name + commit date
                "--date=short",            # date in YYYY-MM-DD format
            ],
            text=True
        )
    except subprocess.CalledProcessError as e:
        print("Error calling git:", e)
        sys.exit(1)

    # Process each commit line
    for line in git_log_output.splitlines():
        # Format: "Author Name\tYYYY-MM-DD"
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        author_name, commit_date = parts
        acronym = get_acronym(author_name)

        # Determine key (by day or by month)
        if monthly_mode:
            # e.g. '2024-12' for monthly aggregation
            date_key = commit_date[:7]
        else:
            # e.g. '2024-12-13' for daily aggregation
            date_key = commit_date

        daily_commits[date_key][acronym] += 1

    # Sort the date keys (either YYYY-MM-DD or YYYY-MM)
    sorted_dates = sorted(daily_commits.keys())

    # Print results
    # Example for daily mode: 2024-12-13: AH 1, BC 2
    # Example for monthly mode: 2024-12: AH 1, BC 2
    for date_key in sorted_dates:
        commits_sorted = sorted(daily_commits[date_key].items())
        commit_str = ", ".join(f"{acronym} {count}" for acronym, count in commits_sorted)
        print(f"{date_key}: {commit_str}")

if __name__ == "__main__":
    main()
