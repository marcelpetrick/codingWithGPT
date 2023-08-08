from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_0.work_item_tracking.models import Wiql
import pprint


def get_pat_from_file(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()


# todo:
# 'System.CreatedDate':
# Microsoft.VSTS.Common.ResolvedDate':
# 'Microsoft.VSTS.Common.ClosedDate':
# also report title and type
# 'System.WorkItemType': 'Bug',
#  'System.Title': 'Shutdown - Gerät schaltet sich nicht automatisch ab nach '
#                  'Beendigung des Garprogramms',

def parse_metadata_from_ticket(work_item):
    fields = work_item.fields
    created_date = fields['System.CreatedDate']
    return created_date


# Fill in with your personal access token and org URL
personal_access_token = get_pat_from_file('test_pat_full_access.txt')
organization_url = 'https://dev.azure.com/bora-devops'

# Create a connection to the org
credentials = BasicAuthentication('', personal_access_token)
connection = Connection(base_url=organization_url, creds=credentials)

# Get a client (the "core" client provides access to projects, teams, etc)
core_client = connection.clients.get_core_client()

# Get the first page of projects
get_projects_response = core_client.get_projects()

# Get the second project
project = get_projects_response[1]

# Get the Work Item Tracking client
wit_client = connection.clients.get_work_item_tracking_client()

# Get work items for the second project with the tag 'Update_3'
wiql = """
SELECT [System.Id], [System.Title], [System.State]
FROM workitems
WHERE [System.TeamProject] = @project
AND [System.Tags] CONTAINS 'Update_3'
AND [System.Tags] CONTAINS 'DMO_toImplement'
"""
wiql = wiql.replace("@project", "'" + project.name + "'")
wiql_object = Wiql(query=wiql)
query_result = wit_client.query_by_wiql(wiql_object)

# Print out each work item
for work_item in query_result.work_items:
    print("-- workitem --")
    print(work_item)
    print(work_item.id)

    #fetch_and_parse_dates(work_item.url, personal_access_token)
    work_item_result = wit_client.get_work_item(work_item.id)
    print(f"work_item: {work_item_result}")
    pprint.pprint(work_item_result.fields)
    print("fields:", work_item_result.fields)

    print(parse_metadata_from_ticket(work_item_result)) # todo continue here

print(f"amount of found tickets: {len(query_result.work_items)}")

