import requests

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
                        "text": "What is the sum to pay in the given sales slip? It is a german sales slip for groceries or gas. Search for someethhing like `Summe` or `zu zahlen`. Just return the sum in format Euro.cent. No other return text in the return. If no number was found, return NaN."
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
    print(response.json())

#--------------------

import os
import base64
from PIL import Image

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

  def resize_and_convert_images(self) -> None:
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
            send_base64_image_to_openai(base64_encoded_img.decode('utf-8'), api_key)


      except Exception as e:
        print(f"Error processing image {image_path}: {e}")


# Example usage
if __name__ == "__main__":
  directory_path = "test_images"  # Update this to the directory you want to scan
  scanner = ImageScanner(directory_path)
  scanner.scan_for_images()
  # check result with: https://base64.guru/converter/decode/image
  scanner.resize_and_convert_images()

# ---------
# result:
# (venv) [mpetrick@marcel-precision3551 SalesSlipScanner]$ python3 salesSlipScanner.py
# {'id': 'chatcmpl-8qUU2VewcVher85jjuiofq0kB30pG', 'object': 'chat.completion', 'created': 1707520926, 'model': 'gpt-4-1106-vision-preview', 'usage': {'prompt_tokens': 838, 'completion_tokens': 3, 'total_tokens': 841}, 'choices': [{'message': {'role': 'assistant', 'content': '10,93'}, 'finish_reason': 'stop', 'index': 0}]}
# {'id': 'chatcmpl-8qUUE8qnpxSXleSDlyT8xJtRrgmD5', 'object': 'chat.completion', 'created': 1707520938, 'model': 'gpt-4-1106-vision-preview', 'usage': {'prompt_tokens': 838, 'completion_tokens': 3, 'total_tokens': 841}, 'choices': [{'message': {'role': 'assistant', 'content': '79.49'}, 'finish_reason': 'stop', 'index': 0}]}
# {'id': 'chatcmpl-8qUUJPr8NwVK3W8FTRCDCF7WJFmKc', 'object': 'chat.completion', 'created': 1707520943, 'model': 'gpt-4-1106-vision-preview', 'usage': {'prompt_tokens': 838, 'completion_tokens': 3, 'total_tokens': 841}, 'choices': [{'message': {'role': 'assistant', 'content': '28.41'}, 'finish_reason': 'stop', 'index': 0}]}
#
# So it works :)
#
# TODO: parse the "content" and print the given file-name and the found content.
#