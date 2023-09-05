from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_0.work_item_tracking.models import Wiql
from datetime import datetime


class AzureDevOpsClient:
    def __init__(self, pat_file, organization_url):
        self.pat = self._get_pat_from_file(pat_file)
        self.organization_url = organization_url
        self.credentials = BasicAuthentication('', self.pat)
        self.connection = Connection(base_url=self.organization_url, creds=self.credentials)

    @staticmethod
    def _get_pat_from_file(file_path):
        with open(file_path, 'r') as file:
            return file.read().strip()

    def get_project(self, index=1):
        core_client = self.connection.clients.get_core_client()
        get_projects_response = core_client.get_projects()
        return get_projects_response[index]

    def query_work_items(self, project_name, tags):
        wit_client = self.connection.clients.get_work_item_tracking_client()
        wiql = """
        SELECT [System.Id], [System.Title], [System.State]
        FROM workitems
        WHERE [System.TeamProject] = @project
        """
        for tag in tags:
            wiql += f"AND [System.Tags] CONTAINS '{tag}'\n"
        wiql = wiql.replace("@project", f"'{project_name}'")
        wiql_object = Wiql(query=wiql)
        return wit_client.query_by_wiql(wiql_object).work_items

    @staticmethod
    def _parse_date(date_str):
        try:
            # Try parsing without fractional seconds first
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            # If the above fails, try parsing with fractional seconds
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')

    def parse_metadata_from_ticket(self, work_item):
        wit_client = self.connection.clients.get_work_item_tracking_client()
        work_item_result = wit_client.get_work_item(work_item.id)
        fields = work_item_result.fields

        # Convert dates to the desired format
        created_date_str = fields.get('System.CreatedDate', None)
        if created_date_str:
            created_date_dt = self._parse_date(created_date_str)
            created_date = created_date_dt.strftime('%d.%m.%Y')
        else:
            created_date = None

        resolved_date_str = fields.get('Microsoft.VSTS.Common.ResolvedDate', None)
        if resolved_date_str:
            resolved_date_dt = self._parse_date(resolved_date_str)
            resolved_date = resolved_date_dt.strftime('%d.%m.%Y')
        else:
            resolved_date = None

        closed_date_str = fields.get('Microsoft.VSTS.Common.ClosedDate', None)
        if closed_date_str:
            closed_date_dt = self._parse_date(closed_date_str)
            closed_date = closed_date_dt.strftime('%d.%m.%Y')
        else:
            closed_date = None

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
    @staticmethod
    def write_list_of_dict_to_file(data):
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

    print(f"amount of found tickets: {len(parsed_work_items)}")

    FileWriter.write_list_of_dict_to_file(parsed_work_items)
