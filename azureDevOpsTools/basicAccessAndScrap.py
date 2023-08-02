import os
import requests
from datetime import datetime, timedelta

# Fetch the PAT from environment variables
PAT = os.getenv('PAT')
print(f'PAT: {PAT}')
# Rest of your script continues here...

# Replace with your project URL
#project_url = 'https://dev.azure.com/YOUR_ORGANIZATION/YOUR_PROJECT/_apis/wit/wiql?api-version=6.0'
project_url = 'https://dev.azure.com/bora-devops/P118_HMI/_apis/wit/wiql?api-version=6.0'
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Basic {PAT}'
}

# Query to get work items that have been changed in the past two days with the tag "Update3"
query = {
    "query": """
    SELECT [System.Id], [System.Title], [System.Tags] 
    FROM workitems 
    WHERE [System.TeamProject] = @project
    AND [System.ChangedDate] >= @today-2
    AND [System.Tags] CONTAINS 'Update_3'
    """
}

response = requests.post(project_url, json=query, headers=headers)

if response.status_code == 200:
    work_items = response.json()['workItems']
    for item in work_items:
        print(f"ID: {item['id']} - URL: {item['url']}")
else:
    print(f"Error fetching work items: {response.text}")


