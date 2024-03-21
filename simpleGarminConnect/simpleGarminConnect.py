import json
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)


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


def main():
    """
    Main function to log into Garmin Connect and fetch user profile information.
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
        print(json.dumps(user_profile, indent=4, sort_keys=True))

    except (GarminConnectConnectionError,
            GarminConnectAuthenticationError,
            GarminConnectTooManyRequestsError) as err:
        print(f"Error occurred during Garmin Connect Client process: {err}")
    except KeyError:
        print("Invalid format of credentials file. Please check the email and password keys.")


if __name__ == "__main__":
    main()
