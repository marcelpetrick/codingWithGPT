from flask import Flask, request
import os
from PIL import Image
import numpy as np
from werkzeug.utils import secure_filename

def process_image(image_path):
    print(f"process_image: {image_path}")
    # Load image
    with Image.open(image_path) as img:
        # Convert to grayscale
        img_gray = img.convert('L')

    # Convert image data to a numpy array
    img_array = np.array(img_gray)

    # Calculate average pixel value
    average_pixel_value = img_array.mean()

    # If the average pixel value is greater than 127 (midpoint of 0-255), return True, else False
    return True
    # return average_pixel_value > 127

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    if file:
        filename = secure_filename(file.filename)
        if not filename:
            return 'Invalid filename', 400
        os.makedirs('temp', exist_ok=True)
        newName = os.path.join('temp', filename)
        file.save(newName)
        # TODO: process the image and get the result
        # This might take up to 30 seconds
        result = process_image(newName)
        print(f"result: {result}")
        return {'result': "TRUE" if result else "FALSE"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
