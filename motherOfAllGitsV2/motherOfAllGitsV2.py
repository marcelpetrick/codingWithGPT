import requests
import subprocess
import json


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
                try:
                    if repo['private']:
                        print("! private repo !")
                        clone_url = clone_url.replace('https://', f'https://{token}@')

                    subprocess.run(["git", "clone", clone_url])
                    print(f"Cloned {repo['name']}")
                except Exception as e:
                    print(f"Error cloning {repo['name']}: {e}")

            # Check for the 'next' page link
            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                url = None
        else:
            print(f"Failed to fetch repositories: {response.status_code}")
            break

clone_all_repos("github_credentials.json")
