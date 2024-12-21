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

# !/usr/bin/env python3

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
    print(f"Usage: {sys.argv[0]} /path/to/repo [--month] [--bars]")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        usage_and_exit()

    # Mode flags
    monthly_mode = False
    bars_mode = False

    # Parse arguments (beyond the script name)
    # We expect the last non-flag argument to be the repo path
    args = sys.argv[1:]

    # We’ll store the repo path after processing flags
    repo_path = None

    # Collect recognized flags; whichever remain at the end,
    # we assume the last one is the repo path
    recognized_flags = {"--month", "--bars"}

    # Let's store non-flag args in a list
    non_flag_args = []

    for arg in args:
        if arg in recognized_flags:
            if arg == "--month":
                monthly_mode = True
            elif arg == "--bars":
                bars_mode = True
        else:
            # Not a recognized flag, so we assume it's the repo path
            non_flag_args.append(arg)

    # After processing, we expect exactly 1 non-flag argument: the repo path
    if len(non_flag_args) != 1:
        usage_and_exit()

    repo_path = non_flag_args[0]

    # Data structure to collect commits by day or month
    # Structure: { dateKey: { 'ACRONYM': count, ... }, ... }
    daily_commits = defaultdict(lambda: defaultdict(int))

    # Gather git log data
    try:
        git_log_output = subprocess.check_output(
            [
                "git",
                "-C", repo_path,
                "log",
                "--use-mailmap",  # respects .mailmap
                "--pretty=format:%aN\t%ad",  # Author name + commit date
                "--date=short",  # date in YYYY-MM-DD format
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

    # Sort the date keys (either YYYY-MM or YYYY-MM-DD)
    sorted_dates = sorted(daily_commits.keys())

    # Print results
    # 1) If --bars is used, we only print total commits and a "bar".
    #    Example: 2024-12-13: 5: ▒▒▒▒▒
    # 2) Otherwise, we list the author acronyms and counts.
    if bars_mode:
        for date_key in sorted_dates:
            # Sum all commits for that date key
            total_count = sum(daily_commits[date_key].values())
            bar_str = "▒" * total_count
            print(f"{date_key}: {total_count}: {bar_str}")
    else:
        for date_key in sorted_dates:
            commits_sorted = sorted(daily_commits[date_key].items())
            commit_str = ", ".join(f"{acronym} {count}" for acronym, count in commits_sorted)
            print(f"{date_key}: {commit_str}")


if __name__ == "__main__":
    main()
