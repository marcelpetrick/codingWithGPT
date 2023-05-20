import requests
import time
import os
import glob
import sys

def send_file(filename):
    #url = 'http://127.0.0.1:5000/upload' # local development
    #url = 'http://marcel-precision3551:5000/upload' # host: laptop
    url = 'http://malina400:5000/upload' # host: the rpi
    files = {'file': open(filename, 'rb')}

    response = requests.post(url, files=files)
    if response.ok:
        print('response:', response.json())  # should print the result: {'result': True/False}
        print("  ", response.json().get("result"))
        return True if response.json().get("result") == "TRUE" else False
    else:
        print('Error:', response.text)
        return False

def processWithTiming(filename):
    startTime = time.time()
    result = send_file(filename)
    print(f"  processing took {time.time()-startTime}: result = {result}")
    return result

# processWithTiming('mojo.gif') # FALSE
# processWithTiming('cat.gif') # FALSE
# processWithTiming('frame09.gif') # TRUE

# goal: get all files from tempgifs together with the given number as input; check with the send_file method - in case of any true, abort rest of the evaluation
# return the result


def detect_cat(images):

    for image in images:
        print("detect_cat: image now in processing:", image)
        normPath = os.path.normpath(image)
        #print("  -> normPath: ", normPath)
        # Replace single slashes with double slashes
        double_slash_path = normPath.replace(os.sep, "//")
        #print("  -> double_slash_path: ", double_slash_path)

        prediction = processWithTiming(double_slash_path)
        if prediction:
            return True

    return False

def str_to_int(s):
    """
    Converts a string that contains a number (possibly with leading alphabetic characters) to an integer.

    :param s: The string to be converted.
    :type s: str
    :return: The converted integer and a boolean indicating success or failure.
    :rtype: tuple
    """

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
    """
    Retrieves image paths from a given directory up to a maximum number.

    :param path: Directory path to search for images.
    :type path: str
    :param max_number: Maximum number of image paths to retrieve.
    :type max_number: int
    :return: List of image paths.
    :rtype: list
    """
    image_paths = []

    current_directory = os.getcwd()
    #print(f"current working directory: {current_directory}")

    # The glob.glob function returns a list of paths matching the specified pathname pattern.
    # The pattern here is "*.[jpg|gif]", which matches all .jpg and .gif files in the directory specified by path.
    all_images = sorted(glob.glob(os.path.join(path, "*.jpg")) + glob.glob(os.path.join(path, "*.gif")))
    #print("all images:", all_images)

    # Loop through the images and add paths to the image_paths list until the specified number is reached
    for image in all_images:
        # Extract the number from the image file name using os.path.basename to get the file name,
        # and then using .split and .strip to extract the number
        baseName = os.path.basename(image).split('.')[0]
        image_number, success = str_to_int(baseName)
        if success:
            #print(f"The converted value is {image_number}.")
            # Add the image path to the image_paths list if the image number is less than the specified number
            if image_number < maxNumber:
                image_paths.append(image)
        else:
            print("Error: the string does not contain a valid integer.")

    return image_paths

def detect_cats(path_to_check, frames_to_process):
    """
    Detects if a cat exists in any image from a given directory using the YOLOv5 model.

    :param path_to_check: Directory path to search for images.
    :type path_to_check: str
    :param frames_to_process: Maximum number of images to process.
    :type frames_to_process: int
    :return: True if a cat is detected in any image, False otherwise.
    :rtype: bool
    """
    # step `prepare`: find all jpg images in the folder and put them up to the given number into a list
    images = get_image_paths(path_to_check, frames_to_process)
    # Check if there's a cat in any of the images
    cat_detected = detect_cat(images)

    if cat_detected:
        print("A cat was detected in one of the images.")
        return True
    else:
        print("No cat was detected in one of the images.")

    return False


# taken from the caller-stub
if __name__ == "__main__":
    startTime = time.time()
    path_to_check = sys.argv[1]
    frames_to_process = int(sys.argv[2])
    result = detect_cats(path_to_check, frames_to_process)
    endTime = time.time()
    print("Cat detection took: ", endTime - startTime, " seconds")
    sys.exit(0 if result else 1)