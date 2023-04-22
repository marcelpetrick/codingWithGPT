# write me a python function which takes a filepath to a directory. i have already the caller code. let's call this function "changeScreenshotNamesIntoImg00Tonn".  So it should do the following: 1. find all image-format files and put them to a list. 2. sort this list ascending by name. 3. Change the files filenames into "imgXX" where XX stands for 00, 01, 02, 03 .. and so on. Keep the file-extension from the original name.

import sys # had to fix this import, was os
from pathlib import Path
from typing import List

def changeScreenshotNamesIntoImg00Tonn(directory: str) -> None:
    img_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')

    def is_image_file(file: Path) -> bool:
        return file.suffix.lower() in img_extensions

    def get_image_files(dir_path: Path) -> List[Path]:
        return sorted([file for file in dir_path.iterdir() if file.is_file() and is_image_file(file)])

    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"Error: {directory} is not a valid directory.")
        return

    image_files = get_image_files(dir_path)

    for index, image_file in enumerate(image_files):
        new_filename = f"img{index:02d}{image_file.suffix}"
        new_filepath = dir_path / new_filename
        image_file.rename(new_filepath)
        print(f"{image_file.name} -> {new_filename}")

# Example usage:
# changeScreenshotNamesIntoImg00Tonn("/path/to/your/directory")

#-------------------------------------------

if __name__ == "__main__":
    path_arg = None
    if len(sys.argv) > 1:
        path_arg = sys.argv[1]
    print("path_arg:", path_arg)
    changeScreenshotNamesIntoImg00Tonn(path_arg)


#-------------------------------------------

# example call
# PS C:\mpetrick\repos\codingWithGPT> python .\changeScreenshotNamesIntoImg00Tonn.py "C:\\Users\\mpetrick\\Pictures\\Screenshots\\foo"
# path_arg: C:\\Users\\mpetrick\\Pictures\\Screenshots\\foo
# Screenshot 2023-04-21 110220.png -> img00.png
# Screenshot 2023-04-21 110520.png -> img01.png
# Screenshot 2023-04-21 110605.png -> img02.png
# Screenshot 2023-04-21 110719.png -> img03.png
# Screenshot 2023-04-21 110730.png -> img04.png
# Screenshot 2023-04-21 111042.png -> img05.png
# Screenshot 2023-04-21 111340.png -> img06.png
# Screenshot 2023-04-21 111539.png -> img07.png
# Screenshot 2023-04-21 111710.png -> img08.png
# Screenshot 2023-04-21 112044.png -> img09.png
# PS C:\mpetrick\repos\codingWithGPT>
