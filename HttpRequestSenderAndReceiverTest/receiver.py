import socket
import os

from PIL import Image
import numpy as np


def process_image(image_path):
    # Load image
    with Image.open(image_path) as img:
        # Convert to grayscale
        img_gray = img.convert('L')

    # Convert image data to a numpy array
    img_array = np.array(img_gray)

    # Calculate average pixel value
    average_pixel_value = img_array.mean()

    # If the average pixel value is greater than 127 (midpoint of 0-255), return True, else False
    return average_pixel_value > 127


def process_data(data):
    # Save the data to a file
    with open('/path/to/save/image.jpg', 'wb') as f:
        f.write(data)
    # TODO: process the image and get the result
    # This might take up to 30 seconds
    result = process_image('mojo.gif')
    return result

def start_server():
    host = '0.0.0.0'
    port = 5000

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            data = conn.recv(1024)
            result = process_data(data)
            conn.sendall(bytes(str(result), 'utf-8'))

start_server()
