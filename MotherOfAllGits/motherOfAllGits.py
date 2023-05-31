# Write me a python3 script, which takes a github user-name (like "marcelpetrick") and then retrieves a list of all the available repositories. Most likely those will be just the publicly visible. But if there is a way to see the invisible ones, then tell me as well.
# The script should also allow to clone all those repositories to a given path. clone one by one repo.
import requests
import os # why?
import subprocess

def get_repos(username):
    url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(url)
    repos = response.json()
    return [repo['clone_url'] for repo in repos]

def clone_repos(repos, path):
    for repo in repos:
        subprocess.run(['git', 'clone', repo], cwd=path)

def main():
    username = input("Enter GitHub username: ")
    path = input("Enter path to clone repositories: ")
    repos = get_repos(username)
    clone_repos(repos, path)

if __name__ == "__main__":
    main()
