from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import pprint

def get_pat_from_file(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()

# Fill in with your personal access token and org URL
personal_access_token = get_pat_from_file('test_pat_full_access.txt')
print(f"personal_access_token: {personal_access_token}")
organization_url = 'https://dev.azure.com/bora-devops'

# Create a connection to the org
credentials = BasicAuthentication('', personal_access_token)
connection = Connection(base_url=organization_url, creds=credentials)

# Get a client (the "core" client provides access to projects, teams, etc)
core_client = connection.clients.get_core_client()

# Get the first page of projects
get_projects_response = core_client.get_projects()
print(f"get_projects_response: {get_projects_response}")
index = 0
for project in get_projects_response:
    pprint.pprint("[" + str(index) + "] " + project.name)
    index += 1
