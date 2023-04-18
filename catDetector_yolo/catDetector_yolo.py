# both: https://64.media.tumblr.com/f2642e16b4e35e03fb78974bf4682014/87afdb1757d216d5-02/s500x750/4351c8582650e748af424110c25ac9a316f74443.gifv

# prompt:
# I want to write a python script which uses yolo in version5 (or newer) to check a webp-image. This is an animated format. And the file is stored on tumblr, so it have to be downloaded first. The script should tell me if an object of class cat is in that webp-image. Write me code for that.

# result:
# Replace https://your-tumblr-url.com/your-image.webp with the actual URL of the webp-image on Tumblr. You'll also need to download the YOLOv5 pre-trained weights (e.g., yolov5s.pt) from the YOLOv5 GitHub repository and place it in the same directory as the script.
#
# Run the script, and it will tell you if a cat is detected in the webp-image

# Give me a pip command for all the imports
# pip install yolov5 opencv-python requests pywebp

import os
import cv2 # dead include?
import requests
from pywebp import WebP
import tempfile
from yolov5 import YOLOv5


# Download the webp-image from Tumblr
def download_image(url, filepath):
    response = requests.get(url)
    with open(filepath, 'wb') as file:
        file.write(response.content)


# Convert animated WebP to a series of images
def webp_to_images(webp_file):
    with WebP(webp_file) as webp:
        images = [frame.as_opencv() for frame in webp]
    return images


# Check if there's a cat in any of the images
def detect_cat(images, yolo):
    for image in images:
        results = yolo.predict(image)
        for result in results:
            if result['class'] == 'cat':
                return True
    return False


def main():
    # Set the URL of the webp-image on Tumblr
    #url = 'https://your-tumblr-url.com/your-image.webp' # from prompt
    url = 'https://64.media.tumblr.com/f2642e16b4e35e03fb78974bf4682014/87afdb1757d216d5-02/s500x750/4351c8582650e748af424110c25ac9a316f74443.gifv' # mine - but gifv, ugh

    # Download the image
    with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as tmp_webp:
        download_image(url, tmp_webp.name)

    # Convert the WebP to images
    images = webp_to_images(tmp_webp.name)
    os.unlink(tmp_webp.name)

    # Initialize YOLOv5 model
    yolo = YOLOv5('yolov5s.pt')

    # Check if there's a cat in any of the images
    cat_detected = detect_cat(images, yolo)

    if cat_detected:
        print("A cat was detected in the webp-image.")
    else:
        print("No cat was detected in the webp-image.")


if __name__ == '__main__':
    main()
