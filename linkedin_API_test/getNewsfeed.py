import configparser
import os
from linkedin_api import Linkedin

def read_credentials(config_file):
    """Reads credentials from the given INI file."""
    config = configparser.ConfigParser()
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")

    config.read(config_file)

    if 'linkedin' not in config:
        raise ValueError("Missing 'linkedin' section in configuration file.")

    email = config['linkedin'].get('email')
    password = config['linkedin'].get('password')

    if not email or not password:
        raise ValueError("Email or password missing in configuration file.")

    return email, password

def main():
    # Path to the configuration file
    config_file = 'config.ini'

    try:
        # Read email and password from the configuration file
        email, password = read_credentials(config_file)

        # Log in to LinkedIn
        api = Linkedin(email, password)
        print("Successfully logged in to LinkedIn!")

        # Fetch and display newsfeed post URNs
        newsfeed = api.get_news_feed()
        post_urns = [post['entityUrn'] for post in newsfeed if 'entityUrn' in post]
        print("Post URNs from your newsfeed:")
        for urn in post_urns:
            print(urn)

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
