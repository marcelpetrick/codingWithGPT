# Write me a python3 script, which takes a github user-name (like "marcelpetrick") and then retrieves a list of all the available repositories. Most likely those will be just the publicly visible. But if there is a way to see the invisible ones, then tell me as well.
# The script should also allow to clone all those repositories to a given path. clone one by one repo.

import requests
import subprocess
import argparse

# beware: will only get the very first 100 repos - else use the Github API
def get_repos(username):
    page = 1
    repos = []
    while True:
        url = f"https://api.github.com/users/{username}/repos?page={page}&per_page=100"
        response = requests.get(url)
        if response.status_code != 200:
            break
        current_page_repos = response.json()
        if not current_page_repos:
            break
        repos.extend(current_page_repos)
        page += 1
    return [repo['clone_url'] for repo in repos]

def clone_repos(repos, path):
    for repo in repos:
        subprocess.run(['git', 'clone', repo], cwd=path)

def main():
    parser = argparse.ArgumentParser(description='Clone all public repositories for a given GitHub user.')
    parser.add_argument('name', type=str, help='GitHub username')
    parser.add_argument('target', type=str, help='Path to clone repositories')
    args = parser.parse_args()

    repos = get_repos(args.name)
    clone_repos(repos, args.target)

if __name__ == "__main__":
    main()

# python3 motherOfAllGits.py marcelpetrick ../../MotherOfAllGitsOutput
