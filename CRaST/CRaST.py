import requests
import time

def download_file(url):
    """
    Downloads a file from the specified URL and measures the download time and speed.
    Prints the results in a single line with an ISO 8601 timestamp.

    Args:
        url (str): The URL of the file to be downloaded.
    """
    try:
        start_time = time.time()
        response = requests.get(url)
        end_time = time.time()

        if response.status_code == 200:
            file_size = len(response.content) / (1024 * 1024)  # File size in MB
            download_time = end_time - start_time  # Time in seconds
            download_speed = (file_size * 8) / download_time  # Speed in Mbps

            # ISO 8601 Time Format: HH:MM:SS
            current_time = time.strftime("%H:%M:%S")

            print(f"{current_time} | File Size: {file_size:.2f} MB | Time: {download_time:.2f} s | Speed: {download_speed:.2f} Mbps")
        else:
            print(f"{time.strftime('%H:%M:%S')} | Failed to download file. Status: {response.status_code}")
    except requests.RequestException as e:
        print(f"{time.strftime('%H:%M:%S')} | Error: {e}")

def main():
    """
    Main function for downloading a file at regular intervals and logging the download speed.
    """
    #url = "https://random-data-api.com/api/v2/users?size=100" # URL of the file to be downloaded - sadly only 0.08 MB
    url = "https://archive.org/download/4-mlinux-32.0-core/grub2-boot.iso" # 7.7 MB

    while True:
        download_file(url)
        time.sleep(10)  # Wait 10 seconds before next download

if __name__ == "__main__":
    main()
