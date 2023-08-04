import requests


def get_pat_from_file(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()


def get_projects(pat):
    url = 'https://dev.azure.com/bora-devops/_apis/projects'
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + pat
    }

    response = requests.get(url, headers=headers)
    print(f"response: {response}")

    print("status_code:", response.status_code) # 203 is response from cache
    if response.status_code == 200:
        return response.json()
    else:
        return None


if __name__ == '__main__':
    pat = get_pat_from_file('test_pat_full_access.txt')
    projects = get_projects(pat)
    print(f"projects: {projects}")
    if projects:
        for project in projects['value']:
            print('Project: ', project['name'])
    else:
        print('Error fetching projects')

#------------------------------------
# /home/mpetrick/repos/epdserver/.venv/bin/python3 /home/mpetrick/repos/codingWithGPT/azureDevOpsTools/basicAccessAndScrap.py
# response: <Response [203]>
# status_code: 203
# projects: None
# Error fetching projects
#
# Process finished with exit code 0
