import os
import subprocess
import requests
import json


def clone_or_update_repo(repo_url, repo_name, token):
    if os.path.isdir(repo_name):
        # Change to the repo directory
        os.chdir(repo_name)

        # Pull the latest changes
        try:
            subprocess.run(["git", "pull"], check=True)
            print(f"Updated repository: {repo_name}")
        except subprocess.CalledProcessError as e:
            print(f"Error updating {repo_name}: {e}")

        # Change back to the original directory
        os.chdir("..")
    else:
        # Clone the repository
        try:
            subprocess.run(["git", "clone", repo_url], check=True)
            print(f"Cloned repository: {repo_name}")
        except subprocess.CalledProcessError as e:
            print(f"Error cloning {repo_name}: {e}")


def clone_all_repos(credentials_file):
    with open(credentials_file, 'r') as file:
        credentials = json.load(file)

    username = credentials['username']
    token = credentials['token']

    # Updated API Endpoint to include private repositories
    # If this one is used, then it will list just public repos of the specific name!
    # url = f"https://api.github.com/users/{username}/repos?per_page=100"
    url = f"https://api.github.com/user/repos?per_page=100"

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            repos = response.json()
            for repo in repos:
                clone_url = repo['clone_url']
                print(f"------------ Cloning {repo['name']} ------------")
                if repo['private']:
                    clone_url = clone_url.replace('https://', f'https://{token}@')
                    print("! private repo !")
                clone_or_update_repo(clone_url, repo['name'], token)

            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                url = None
        else:
            print(f"Failed to fetch repositories: {response.status_code}")
            break

clone_all_repos("github_credentials.json")
