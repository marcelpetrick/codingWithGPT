import json
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)
import datetime

def load_credentials(filename='credentials.json'):
    """
    Loads Garmin Connect account credentials from a specified JSON file.

    :param filename: String, the path to the JSON file containing the credentials.
    :return: Dictionary with 'email' and 'password' keys.
    """
    try:
        with open(filename, 'r') as file:
            credentials = json.load(file)
        return credentials
    except FileNotFoundError:
        print("Credentials file not found. Please ensure the file is in the correct directory.")
        exit(1)
    except json.JSONDecodeError:
        print("Error decoding JSON. Please check the file format.")
        exit(1)


def fetch_running_activities(client):
    """
    Fetches running activities for the current year from the Garmin Connect account.

    :param client: Initialized Garmin client object.
    :return: List of JSON objects, each representing a running activity.
    """
    current_year = datetime.datetime.now().year
    start_date = datetime.date(current_year, 1, 1)
    end_date = datetime.date(current_year, 12, 31)
    print("start_date:", start_date)
    print("end_date:", end_date)

    # Assuming the Garmin client has a method to fetch activities by date range.
    # This is a placeholder and may need adjustment based on actual package capabilities.
    activities = client.get_activities_by_date(start_date, end_date)
    #print("activities:", activities)

    # Filter for running activities - This step may need to be adjusted based on the actual data structure
#    running_activities = [activity for activity in activities if activity['activityType'] == 'running']

    # Assuming activities is a list of dictionaries representing activities
    running_activities = [activity for activity in activities if activity['activityType']['typeKey'] == 'running']

    total_activities = len(running_activities)
    print(f"Total number of running activities: {total_activities}")

    return running_activities

def main():
    """
    Main function to log into Garmin Connect, fetch user profile information,
    and retrieve running activities for the current year.
    """
    try:
        # Load credentials
        credentials = load_credentials()
        email = credentials['email']
        password = credentials['password']

        # Initialize Garmin client with credentials
        client = Garmin(email, password)
        client.login()

        # Fetch and print user profile in a readable format
        user_profile = client.get_user_profile()
        print("User Profile:")
        print(json.dumps(user_profile, indent=4, sort_keys=True))

        # Fetch running activities for the current year
        running_activities = fetch_running_activities(client)
        print("\nRunning Activities for the Current Year:")
        print(json.dumps(running_activities, indent=4, sort_keys=True))

    except (GarminConnectConnectionError,
            GarminConnectAuthenticationError,
            GarminConnectTooManyRequestsError) as err:
        print(f"Error occurred during Garmin Connect Client process: {err}")
    except KeyError:
        print("Invalid format of credentials file. Please check the email and password keys.")

if __name__ == "__main__":
    main()
