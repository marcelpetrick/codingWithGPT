import os
import subprocess
import requests
import json

def clone_or_update_repo(repo_url, repo_name, token, output_path):
    """
    Clone or update a given repository.

    :param repo_url: URL of the repository to clone or update.
    :param repo_name: Name of the repository.
    :param token: Personal Access Token for GitHub.
    :param output_path: Directory path where the repository will be cloned or updated.
    :return: None
    """
    repo_path = os.path.join(output_path, repo_name)
    if os.path.isdir(repo_path):
        os.chdir(repo_path)
        try:
            subprocess.run(["git", "pull"], check=True)
            print(f"Updated repository: {repo_name}")
        except subprocess.CalledProcessError as e:
            print(f"Error updating {repo_name}: {e}")
        os.chdir(output_path)
    else:
        try:
            subprocess.run(["git", "clone", repo_url, repo_path], check=True)
            print(f"Cloned repository: {repo_name}")
        except subprocess.CalledProcessError as e:
            print(f"Error cloning {repo_name}: {e}")

def clone_all_repos(credentials_file, output_path="."):
    """
    Clone all repositories for a given user.

    :param credentials_file: Path to the JSON file containing GitHub credentials.
    :param output_path: Directory path where repositories will be cloned or updated. Default is current directory.
    :return: None
    """
    # Expand the user's home directory path
    output_path = os.path.expanduser(output_path)

    if not os.path.isdir(output_path):
        print(f"Output path {output_path} does not exist.")
        return

    with open(credentials_file, 'r') as file:
        credentials = json.load(file)

    username = credentials['username']
    token = credentials['token']

    url = f"https://api.github.com/user/repos?per_page=100"
    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            repos = response.json()
            for repo in repos:
                clone_url = repo['clone_url']
                print(f"------------ Cloning {repo['name']} ------------")
                if repo['private']:
                    clone_url = clone_url.replace('https://', f'https://{token}@')
                    print("Note: private repository")
                clone_or_update_repo(clone_url, repo['name'], token, output_path)
                print("")  # newline as separator

            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                url = None
        else:
            print(f"Failed to fetch repositories: {response.status_code}")
            break

# Example usage
# clone_all_repos("github_credentials.json", "/path/to/output/directory")
clone_all_repos("github_credentials.json", "~/output_motherOfAllGitsV2")
