# from openai import OpenAI
#
# # OPENAI_API_KEY must be set
# client = OpenAI()
#
# response = client.chat.completions.create(
#   model="gpt-4-vision-preview",
#   messages=[
#     {
#       "role": "user",
#       "content": [
#         {"type": "text", "text": "What’s in this image?"},
#         {
#           "type": "image_url",
#           "image_url": {
#             "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
#           },
#         },
#       ],
#     }
#   ],
#   max_tokens=300,
# )
#
# print(response.choices[0])
#

# -------------

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
            print(base64_encoded_img.decode('utf-8'))

      except Exception as e:
        print(f"Error processing image {image_path}: {e}")


# Example usage
if __name__ == "__main__":
  directory_path = "test_images"  # Update this to the directory you want to scan
  scanner = ImageScanner(directory_path)
  scanner.scan_for_images()
  # check result with: https://base64.guru/converter/decode/image
  scanner.resize_and_convert_images()
