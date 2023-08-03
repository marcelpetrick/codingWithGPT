import os
# Fetch the PAT from environment variables
PAT = os.getenv('PAT')
print(f'PAT: {PAT}')
organization_url = 'https://dev.azure.com/bora-devops/P118_HMI/_apis/wit/wiql?api-version=6.0'

from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import pprint

# replace these with your own values
#organization_url = "https://dev.azure.com/your-organization"
organization_url = 'https://dev.azure.com/bora-devops/P118_HMI'
pat = PAT #"your-personal-access-token"

credentials = BasicAuthentication('', pat)
connection = Connection(base_url=organization_url, creds=credentials)

client = connection.clients.get_work_item_tracking_client()

# Sample query: Get all work items
wiql = "SELECT [System.Id] FROM workitems"

results = client.query_by_wiql(wiql).work_items

# print all work item IDs
for work_item in results:
    print(work_item.id)


