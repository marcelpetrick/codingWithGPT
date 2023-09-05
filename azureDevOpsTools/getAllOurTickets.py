from azure.devops.connection import Connection
from azure.devops.v7_0.work_item_tracking.models import Wiql
from msrest.authentication import BasicAuthentication
from datetime import datetime


class AzureDevOpsClient:
    """
    A client for interacting with Azure DevOps using a Personal Access Token (PAT).

    Attributes:
        pat (str): Personal Access Token.
        organization_url (str): Azure DevOps organization URL.
        credentials: Azure DevOps credentials.
        connection: Azure DevOps connection object.
    """

    def __init__(self, pat_file, organization_url):
        """
        Initialize AzureDevOpsClient.

        Args:
            pat_file (str): File path to the PAT file.
            organization_url (str): Azure DevOps organization URL.
        """
        self.pat = self._get_pat_from_file(pat_file)
        self.organization_url = organization_url
        self.credentials = BasicAuthentication('', self.pat)
        self.connection = Connection(base_url=self.organization_url, creds=self.credentials)

    @staticmethod
    def _get_pat_from_file(file_path):
        """Retrieve PAT from the given file."""
        with open(file_path, 'r') as file:
            return file.read().strip()

    def get_project(self, index=1):
        """Get the project at the specified index."""
        core_client = self.connection.clients.get_core_client()
        get_projects_response = core_client.get_projects()
        return get_projects_response[index]

    def query_work_items(self, project_name, tags):
        """Query work items for a given project name and tags."""
        wit_client = self.connection.clients.get_work_item_tracking_client()
        wiql = """
        SELECT [System.Id], [System.Title], [System.State]
        FROM workitems
        WHERE [System.TeamProject] = '{}'
        """.format(project_name)
        for tag in tags:
            wiql += "AND [System.Tags] CONTAINS '{}'\n".format(tag)
        wiql_object = Wiql(query=wiql)
        return wit_client.query_by_wiql(wiql_object).work_items

    @staticmethod
    def _parse_date(date_str):
        """Parse a date string into a datetime object, handling multiple formats."""
        try:
            # Try parsing without fractional seconds first
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            # If the above fails, try parsing with fractional seconds
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')

    def parse_metadata_from_ticket(self, work_item):
        """Parse metadata from a given work item."""
        wit_client = self.connection.clients.get_work_item_tracking_client()
        work_item_result = wit_client.get_work_item(work_item.id)
        fields = work_item_result.fields

        # Helper function for date conversion
        def _get_date(field_name):
            date_str = fields.get(field_name, None)
            return self._parse_date(date_str).strftime('%d.%m.%Y') if date_str else None

        # Convert dates to the desired format
        created_date = _get_date('System.CreatedDate')
        resolved_date = _get_date('Microsoft.VSTS.Common.ResolvedDate')
        closed_date = _get_date('Microsoft.VSTS.Common.ClosedDate')

        # Modify title and create URL
        title = f"{work_item_result.id}: {fields.get('System.Title', '')}"
        url = f"https://dev.azure.com/bora-devops/P118_HMI/_workitems/edit/{work_item_result.id}/"

        return {
            'Title': title,
            'URL': url,
            'ID': work_item_result.id,
            'Created Date': created_date,
            'Resolved Date': resolved_date,
            'Closed Date': closed_date,
            'Work Item Type': fields.get('System.WorkItemType', None)
        }


class FileWriter:
    """A simple writer to save data to a file."""

    @staticmethod
    def write_list_of_dict_to_file(data):
        """Write a list of dictionaries to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"tickets_DMO_toImplement_{timestamp}.txt"
        with open(filename, 'w') as file:
            for item in data:
                file.write(f'{str(item)}\n')


if __name__ == '__main__':
    client = AzureDevOpsClient('test_pat_full_access.txt', 'https://dev.azure.com/bora-devops')
    project = client.get_project()
    work_items = client.query_work_items(project.name, ['DMO_toImplement'])

    parsed_work_items = [client.parse_metadata_from_ticket(work_item) for work_item in work_items]

    for item in parsed_work_items:
        print(item)

    print(f"Amount of found tickets: {len(parsed_work_items)}")

    FileWriter.write_list_of_dict_to_file(parsed_work_items)
