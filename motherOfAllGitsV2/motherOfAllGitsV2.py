import requests
import subprocess
import json


def clone_all_repos(credentials_file):
    # Reading credentials from the JSON file
    with open(credentials_file, 'r') as file:
        credentials = json.load(file)

    username = credentials['username']
    token = credentials['token']

    # Endpoint to list GitHub repos for a user
    url = f"https://api.github.com/users/{username}/repos"

    # Adding token for authentication
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # Fetching the repositories
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        repos = response.json()
        for repo in repos:
            # Cloning each repository
            clone_url = repo['clone_url']
            try:
                # Replacing 'https://' with 'https://token@' in the clone URL for private repos
                if repo['private']:
                    clone_url = clone_url.replace('https://', f'https://{token}@')

                subprocess.run(["git", "clone", clone_url])
                print(f"Cloned {repo['name']}")
            except Exception as e:
                print(f"Error cloning {repo['name']}: {e}")
    else:
        print(f"Failed to fetch repositories: {response.status_code}")

# Example usage
# clone_all_repos("github_credentials.json")

# Note: Replace "github_credentials.json" with the path to your actual JSON file containing your GitHub credentials.
