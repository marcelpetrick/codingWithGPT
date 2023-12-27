# GitHub Repository Cloning Script

## Overview
This Python script automates the process of cloning all your GitHub repositories, including private ones. It uses the GitHub API to fetch the list of repositories and then clones them to your local machine.

## Author
Marcel Petrick - mail@marcelpetrick.it

## License
This project is licensed under the GNU General Public License v3.0 (GPLv3).

## Setup

### Prerequisites
- Python installed on your system.
- `git` installed and configured.

### Installation
1. Clone or download this repository to your local machine.
2. Navigate to the directory containing the script.
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration
1. Create a JSON file named `github_credentials.json` in the script directory with the following structure:
   ```json
   {
       "username": "your_github_username",
       "token": "your_personal_access_token"
   }
   ```
   Replace `your_github_username` and `your_personal_access_token` with your GitHub username and Personal Access Token (PAT), respectively.

2. Generating Personal Access Token (PAT):
   - Visit [GitHub's token settings page](https://github.com/settings/tokens).
   - Click on `Generate new token`.
   - Give your token a descriptive name, select the scopes or permissions you'd like to grant this token (at minimum, `repo` for accessing private repositories).
   - Click `Generate token` and copy the token immediately. You won’t be able to see it again!

## Usage
Run the script with the following command:
```bash
python clone_all_repos.py "github_credentials.json"
```
This will clone all the repositories associated with the provided GitHub account into the current directory.

## Support
For support, contact me at mail@marcelpetrick.it
