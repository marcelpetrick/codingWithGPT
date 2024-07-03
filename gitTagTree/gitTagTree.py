import os
import sys
import git
from collections import defaultdict


def generate_mermaid_syntax(repo_path):
    repo = git.Repo(repo_path)

    tags = repo.tags
    branches_with_tags = defaultdict(list)

    # Collect all branches that have tags
    for tag in tags:
        commit = tag.commit
        for branch in repo.branches:
            if commit in branch.commit.iter_parents():
                branches_with_tags[branch].append(tag)

    # Start mermaid diagram
    mermaid_syntax = "graph TD\n"

    # Add nodes and edges for branches with tags
    for branch, tags in branches_with_tags.items():
        mermaid_syntax += f"    subgraph {branch.name}\n"
        for tag in tags:
            mermaid_syntax += f"        {tag.name}({tag.name}) --> |{branch.name}| {tag.commit.hexsha[:7]}\n"
        mermaid_syntax += "    end\n"

    # Handle branches and commits that are necessary to show branching
    all_commits = {tag.commit for tag in tags}
    for branch in branches_with_tags:
        current_commit = branch.commit
        while current_commit and current_commit not in all_commits:
            all_commits.add(current_commit)
            parent = current_commit.parents[0] if current_commit.parents else None
            if parent:
                mermaid_syntax += f"    {parent.hexsha[:7]} --> {current_commit.hexsha[:7]}\n"
            current_commit = parent

    return mermaid_syntax


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_git_repo>")
        sys.exit(1)

    repo_path = sys.argv[1]

    if not os.path.isdir(repo_path):
        print("Error: The specified path is not a directory")
        sys.exit(1)

    try:
        mermaid_syntax = generate_mermaid_syntax(repo_path)
        print(mermaid_syntax)
    except git.exc.InvalidGitRepositoryError:
        print("Error: The specified path is not a valid Git repository")
