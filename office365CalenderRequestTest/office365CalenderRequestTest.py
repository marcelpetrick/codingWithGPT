from O365 import Account
from datetime import datetime


def read_credentials(filename):
    credentials = {}
    with open(filename, 'r') as file:
        for line in file:
            key, value = line.strip().split('=')
            credentials[key] = value
    return credentials

credentials_file = 'not_committed_secret_file.txt'
# filestructure should look like this:
#   CLIENT_ID=your_client_id_here
#   CLIENT_SECRET=your_client_secret_here
# also: is git-ignored
credentials = read_credentials(credentials_file)

client_id = credentials.get('CLIENT_ID')
client_secret = credentials.get('CLIENT_SECRET')

print(f"Client ID: {client_id}")
print(f"Client Secret: {client_secret}")

#------

account = Account(credentials)
if not account.is_authenticated:
    # will open a browser window to perform the OAuth2 login procedure
    account.authenticate(scopes=['basic', 'calendar_all'])

calendar = account.schedule().get_default_calendar()

# Example: List upcoming events
events = calendar.get_events()
for event in events:
    print(event)

# Example: Create a new event
new_event = calendar.new_event()
new_event.subject = "fake meeting"
new_event.start = datetime(2023, 12, 23, 10)
new_event.end = datetime(2023, 12, 23, 11)
new_event.save()
