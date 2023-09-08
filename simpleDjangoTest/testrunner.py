import requests
import time

BASE_URL = "http://localhost:8000"


def put_data(content):
    url = f"{BASE_URL}/putData/"
    try:
        response = requests.post(url, data={'data': content})

        # Checking status code of the response
        if response.status_code != 200:
            print(f"Error posting data: {response.status_code} - {response.text}")
            return

        # Print the actual response content for debugging
        print(f"Server response: {response.text}")

        try:
            print(response.json())
        except ValueError:  # Catch specific JSON decode error
            print("Failed to decode JSON from server's response.")

    except requests.ConnectionError:
        print("Failed to connect to the server.")


def get_data():
    url = f"{BASE_URL}/getData/"
    try:
        response = requests.get(url)

        # Checking status code of the response
        if response.status_code != 200:
            print(f"Error fetching data: {response.status_code} - {response.text}")
            return

        try:
            print(response.json())
        except ValueError:
            print("Failed to decode JSON from server's response.")

    except requests.ConnectionError:
        print("Failed to connect to the server.")


if __name__ == "__main__":
    counter = 0
    while True:
        print(f"Iteration {counter}")

        # Put data
        content = f"This is data for iteration {counter}"
        put_data(content)

        # Get data
        get_data()

        # Wait for 100ms
        time.sleep(0.1)
        counter += 1
