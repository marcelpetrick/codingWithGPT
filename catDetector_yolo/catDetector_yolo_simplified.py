# pip install Pillow

import os
import glob
import sys
import cv2
from yolov5 import YOLOv5

def detect_cat(images, yolo):
    for image in images:
        print("detect_cat: image now in processing: ", image)
        normPath = os.path.normpath(image)
        print("  -> normPath: ", normPath)
        # Replace single slashes with double slashes
        double_slash_path = normPath.replace(os.sep, "//")
        print("  -> double_slash_path: ", double_slash_path)

        # Display the image for 2 seconds
        #cv2.imshow('Image', double_slash_path)
        #cv2.waitKey(500)  # Display for 2000 milliseconds (2 seconds)

        results = yolo.predict(image)
        print("results.names:", results.names)

        for result in results.xyxy:
            print("result:", result)
            for tensor in result: # attention: had to modify this manually: GPT4 was not able to generate proper code to iterate over the list of tensors, always forgot one dimension .. therefore checking the class name was not working
                print("tensor:", tensor)
                class_index = int(tensor[-1].item())  # Get the class index
                class_name = results.names[class_index]  # Get the class name
                print(f"Detected object class: {class_name}")
                if class_name == 'cat':
                    #cv2.destroyAllWindows()  # Close the image window
                    return True

    #cv2.destroyAllWindows()  # Close the image window
    return False

def str_to_int(s):
    # Strip leading alphabetic characters
    s = s.lstrip('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')

    try:
        # Try to convert the string to an integer
        value = int(s)
        return value, True
    except ValueError:
        # If the conversion is not possible, return None and False
        return None, False


def get_image_paths(path, maxNumber):
    image_paths = []

    current_directory = os.getcwd()
    print(f"current working directory: {current_directory}")

    # The glob.glob function returns a list of paths matching the specified pathname pattern.
    # The pattern here is "*.[jpg|gif]", which matches all .jpg and .gif files in the directory specified by path.
    all_images = sorted(glob.glob(os.path.join(path, "*.jpg")) + glob.glob(os.path.join(path, "*.gif")))
    print("all images:", all_images)

    # Loop through the images and add paths to the image_paths list until the specified number is reached
    for image in all_images:
        # Extract the number from the image file name using os.path.basename to get the file name,
        # and then using .split and .strip to extract the number
        baseName = os.path.basename(image).split('.')[0]
        image_number, success = str_to_int(baseName)
        if success:
            print(f"The converted value is {image_number}.")
            # Add the image path to the image_paths list if the image number is less than the specified number
            if image_number < maxNumber:
                image_paths.append(image)
        else:
            print("The string does not contain a valid integer.")

    return image_paths

# result = get_image_paths("testdata//mojo", 12)
# print(f"paths: {result}")

def detect_cats(path_to_check, frames_to_process):
    # step `prepare`: find all jpg images in the folder and put them up to the given number into a list
    # todo
    images = get_image_paths(path_to_check, frames_to_process)

    # Initialize YOLOv5 model
    yolo = YOLOv5('yolov5s.pt')

    # Check if there's a cat in any of the images
    cat_detected = detect_cat(images, yolo)

    if cat_detected:
        print("A cat was detected in one of the images.")
        return True
    else:
        print("No cat was detected in one of the images.")

    return False

# taken from the caller-stub
if __name__ == "__main__":
    path_to_check = sys.argv[1]
    frames_to_process = int(sys.argv[2])
    result = detect_cats(path_to_check, frames_to_process)
    sys.exit(0 if result else 1)

# test call
# python catadetector_yolo_simplified.py testdata//mojo 20
#
# Detected object class: cat
# A cat was detected in one of the images.
# PS C:\mpetrick\repos\codingWithGPT\catDetector_yolo>