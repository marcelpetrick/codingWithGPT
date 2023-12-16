import requests
import time


def download_file(url):
    start_time = time.time() * 1000  # Current time in milliseconds
    response = requests.get(url)
    end_time = time.time() * 1000  # End time in milliseconds

    # Ensure the request was successful
    if response.status_code == 200:
        # Calculate file size in Megabytes (MB)
        file_size = len(response.content) / (1024 * 1024)

        # Calculate the time taken for the download in seconds
        download_time = (end_time - start_time) / 1000  # Convert milliseconds to seconds

        # Calculate download speed in Mbps (Megabits per second)
        # 1 byte = 8 bits, and 1 MB = 8 Mb
        download_speed = (file_size * 8) / download_time

        print(f"Downloaded a file of size {file_size:.2f} MB in {download_time:.2f} seconds")
        print(f"Download Speed: {download_speed:.2f} Mbps")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")


def main():
    url = "https://random-data-api.com/api/v2/users?size=10"  # URL of the file to download

    while True:
        download_file(url)
        time.sleep(10)  # Sleep for 10 seconds before downloading again


if __name__ == "__main__":
    main()
