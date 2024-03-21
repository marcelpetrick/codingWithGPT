import json
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)

# Function to load credentials from JSON file
def load_credentials(filename='credentials.json'):
    with open(filename, 'r') as file:
        credentials = json.load(file)
    return credentials

try:
    # Load credentials
    credentials = load_credentials()
    email = credentials['email']
    password = credentials['password']

    # Initialize Garmin client with your credentials
    client = Garmin(email, password)
    client.login()

    # Fetch your user profile
    user_profile = client.get_user_profile()
    print(user_profile)

    # You can also fetch other data like activities, heart rate, steps, etc.
    # activities = client.get_activities(0,1) # Gets the most recent activity
    # print(activities)

except (
    GarminConnectConnectionError,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
) as err:
    print(f"Error occurred during Garmin Connect Client process: {err}")
except FileNotFoundError:
    print("Credentials file not found. Please ensure the file is in the correct directory.")
except KeyError:
    print("Invalid format of credentials file. Please check the email and password keys.")
