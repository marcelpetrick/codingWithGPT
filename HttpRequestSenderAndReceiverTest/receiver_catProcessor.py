from flask import Flask, request
import os
from PIL import Image
import numpy as np
import glob
import sys
from yolov5 import YOLOv5

def process_image(image_path):
    print(f'process_image: {image_path}')

    results = yolo.predict(image_path)

    for result in results.xyxy:
        # print("result:", result)
        for tensor in result:
            # print("tensor:", tensor)
            class_index = int(tensor[-1].item())  # Get the class index
            class_name = results.names[class_index]  # Get the class name
            print(f'  detected object class: {class_name}')
            if class_name == 'cat':
                return True

    return False


app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    if file:
        # todo make sure the temp-dir exists - else create it. Else the process_image runs on a non-existing file because saving failed.
        newName = os.path.join('temp/', file.filename)
        file.save(newName)
        # process the image and get the result
        result = process_image(newName)
        print(f'result: {result}')
        return {'result': 'TRUE' if result else 'FALSE'}

if __name__ == '__main__':
    # Initialize YOLOv5 model
    yolo = YOLOv5('yolov5s.pt')

    app.run(host='0.0.0.0', port=5000)
