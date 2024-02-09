import requests
import os
import base64
from PIL import Image

def send_base64_image_to_openai(base64_image: str, api_key: str) -> None:
    """
    Sends a base64-encoded image to OpenAI and prints the result.

    Args:
    - base64_image (str): The base64-encoded image string.
    - api_key (str): Your OpenAI API key.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What is the sum to pay in the given sales slip? It is a german sales slip for groceries or gas. Search for someethhing like `Summe` or `zu zahlen`. Just return the sum in format `Euro Comma Cent`. No currency character. No other return text in the response. If no number was found, return NaN."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    #print(f"Response: {response.json()}")
    return response.json()

# ----------------------------

class ImageScanner:
  def __init__(self, directory_path: str):
    self.directory_path = directory_path
    self.supported_extensions = ['.gif', '.jpg', '.png']
    self.image_paths = []

  def scan_for_images(self) -> None:
    """
    Scans the directory for image files and updates the image_paths member with the paths.
    """
    try:
      for root, dirs, files in os.walk(self.directory_path):
        for file in files:
          if any(file.lower().endswith(ext) for ext in self.supported_extensions):
            self.image_paths.append(os.path.join(root, file))
    except Exception as e:
      print(f"Error scanning directory {self.directory_path}: {e}")

  def resize_and_convert_images_and_process(self) -> None:
    """
    Resizes each image where the longest side is at most 1500px, converts to base64, and prints it.
    """
    for image_path in self.image_paths:
      try:
        with Image.open(image_path) as img:
          original_width, original_height = img.size
          scaling_factor = min(1, 1500 / max(original_width, original_height))
          new_size = (int(original_width * scaling_factor), int(original_height * scaling_factor))
          resized_img = img.resize(new_size, Image.Resampling.LANCZOS)

          # Convert image to base64
          with open("temp_resized_image.jpg", "wb") as temp_file:
            resized_img.save(temp_file, format="JPEG")
          with open("temp_resized_image.jpg", "rb") as temp_file:
            base64_encoded_img = base64.b64encode(temp_file.read())
            #print(base64_encoded_img.decode('utf-8'))
            api_key = os.getenv("OPENAI_API_KEY")
            resonse_json = send_base64_image_to_openai(base64_encoded_img.decode('utf-8'), api_key)
            # Accessing and printing the "content"
            content = resonse_json['choices'][0]['message']['content']
            print(f"File: {image_path}, Content: {content}")

      except Exception as e:
        print(f"Error processing image {image_path}: {e}")


# Example usage
if __name__ == "__main__":
  directory_path = "test_images"  # Update this to the directory you want to scan
  scanner = ImageScanner(directory_path)
  scanner.scan_for_images()
  # check result with: https://base64.guru/converter/decode/image
  scanner.resize_and_convert_images_and_process()

# ----------------------------

# result:
# (venv) [mpetrick@marcel-precision3551 SalesSlipScanner]$ python3 salesSlipScanner.py
# File: test_images/slip2_1093.jpg, Content: 10,93
# File: test_images/slip0_7949.jpg, Content: 79,49
# File: test_images/slip1_2841.jpg, Content: 28,41
# (venv) [mpetrick@marcel-precision3551 SalesSlipScanner]$
#
# So it works :)
