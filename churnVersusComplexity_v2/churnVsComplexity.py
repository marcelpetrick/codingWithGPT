# ok, i want to wrte a python program. to measure churn versus some other complexity metric (mabye lines of code per file).
# always write pythonic code. assume you are guido van rossum. use the latest language consturcts for python 3. also document with spyhynx/doxygen everything. write iline comments. encapsulate functionality into methods. make proper errro handling and robust software.
#
#
# ok, so the workflow would be: program, which is called by parameter like this
# "python3 churnVersusComplexity.py <path to the repo>".
#
# program then takes this path and invokes  git commands to get a list of all commits. for each commit analyse which file was changed (put those files into a dictionary). print that list to stdout.
# then for each of the files also analyse the complexity. encapsulate this. complexisty can maybe be measured as LoC (lines of code). or what else would you recommend?
#
# then print finally all files (just basename and ending), next column is complexity, next is how many times changed. and then last the full absolut path (inside the git repo).
#
# go

import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def main(repo_path: str):
    try:
        # Validate and prepare repository path
        repo = Path(repo_path).resolve(strict=True)
        if not (repo / ".git").exists():
            raise ValueError(f"The path {repo} is not a valid git repository.")

        # Get commit data from git repository
        commits = get_all_commits(repo)
        churn_data = collect_churn_data(commits, repo)

        # Calculate complexity and print the report
        print_report(churn_data, repo)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def get_all_commits(repo: Path) -> List[str]:
    """
    Get a list of all commits in the repository.
    :param repo: Path to the repository
    :return: List of commit hashes
    """
    try:
        # Run git log to get all commit hashes
        result = subprocess.run(["git", "log", "--pretty=format:%H", "--no-pager"], cwd=repo, text=True, capture_output=True, check=True)
        return result.stdout.strip().split("\n")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get commits: {e}")


def collect_churn_data(commits: List[str], repo: Path) -> Dict[str, Dict[str, int]]:
    """
    Collect churn data for each file in the repository.
    :param commits: List of commit hashes
    :param repo: Path to the repository
    :return: Dictionary with filenames and their change count and complexity
    """
    churn_data = defaultdict(lambda: {"changes": 0, "complexity": 0})

    try:
        for commit in commits:
            # Run git show to get a list of files changed in the commit
            result = subprocess.run(["git", "show", "--name-only", "--pretty=format:", commit, "--no-pager"], cwd=repo, text=True, capture_output=True, check=True)
            changed_files = result.stdout.strip().split("\n")

            for file_path in changed_files:
                if file_path:
                    churn_data[file_path]["changes"] += 1
                    churn_data[file_path]["complexity"] = calculate_complexity(repo / file_path)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to collect churn data: {e}")

    return churn_data


def calculate_complexity(file_path: Path) -> int:
    """
    Calculate complexity as lines of code (LoC).
    :param file_path: Path to the file
    :return: Number of lines in the file
    """
    if not file_path.is_file():
        return 0

    try:
        with file_path.open("r") as file:
            return sum(1 for _ in file)
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return 0


def print_report(churn_data: Dict[str, Dict[str, int]], repo: Path):
    """
    Print churn vs complexity report.
    :param churn_data: Dictionary containing change counts and complexity for each file
    :param repo: Path to the repository
    """
    header = f"{'File':<30} {'Complexity':<10} {'Changes':<10} {'Path':<50}"
    print(header)
    print("-" * len(header))
    for file_path, metrics in churn_data.items():
        base_name = Path(file_path).name
        complexity = metrics["complexity"]
        changes = metrics["changes"]
        full_path = repo / file_path
        print(f"{base_name:<30} {complexity:<10} {changes:<10} {full_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 churnVersusComplexity.py <path to the repo>", file=sys.stderr)
        sys.exit(1)

    repository_path = sys.argv[1]
    main(repository_path)
