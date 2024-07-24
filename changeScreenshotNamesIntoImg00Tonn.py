# write me a python function which takes a filepath to a directory. i have already the caller code. let's call this
# function "changeScreenshotNamesIntoImg00Tonn".  So it should do the following: 1. find all image-format files and
# put them to a list. 2. sort this list ascending by name. 3. Change the files filenames into "imgXX" where XX stands
# for 00, 01, 02, 03 .. and so on. Keep the file-extension from the original name.
#
# 20240724: expanded; needed output of the markdown-embeddings as well. Also made the code more pythonic and resilient and OOP.

# -------------------------------------------

import sys
from pathlib import Path
from typing import List

class ImageRenamer:
    """
    A class to rename image files in a specified directory to a sequential format (img00, img01, etc.).

    Attributes:
        directory (Path): The directory containing the image files.
    """
    def __init__(self, directory: str) -> None:
        """
        Initializes the ImageRenamer with the directory path.

        @param directory: The directory containing the image files.
        """
        self.directory = Path(directory)
        self.img_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')

    def is_image_file(self, file: Path) -> bool:
        """
        Checks if a file is an image based on its extension.

        @param file: The file to check.
        @return: True if the file is an image, False otherwise.
        """
        return file.suffix.lower() in self.img_extensions

    def get_image_files(self) -> List[Path]:
        """
        Retrieves a sorted list of image files in the directory.

        @return: A sorted list of image files.
        """
        return sorted([file for file in self.directory.iterdir() if file.is_file() and self.is_image_file(file)])

    def rename_images(self) -> None:
        """
        Renames the image files in the directory to a sequential format and prints the markdown embeddings.
        """
        if not self.directory.is_dir():
            print(f"Error: {self.directory} is not a valid directory.")
            return

        image_files = self.get_image_files()
        markdown_embeddings = []

        for index, image_file in enumerate(image_files):
            new_filename = f"img{index:02d}{image_file.suffix}"
            new_filepath = self.directory / new_filename
            try:
                image_file.rename(new_filepath)
                print(f"{image_file.name} -> {new_filename}")
                markdown_embeddings.append(f"![]({new_filename})")
            except Exception as e:
                print(f"Error renaming {image_file.name} to {new_filename}: {e}")

        # Print the markdown embeddings at the end
        if markdown_embeddings:
            print("\n".join(markdown_embeddings))

def main(directory: str) -> None:
    """
    The main function to execute the image renaming process.

    @param directory: The directory containing the image files.
    """
    renamer = ImageRenamer(directory)
    renamer.rename_images()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path_arg = sys.argv[1]
        print(f"path_arg: {path_arg}")
        main(path_arg)
    else:
        print("Error: Please provide a directory path as an argument.")

# -------------------------------------------

# usage Win:
# python .\changeScreenshotNamesIntoImg00Tonn.py "C:\\Users\\mpetrick\\Pictures\\Screenshots"
# usage Linux:
# python changeScreenshotNamesIntoImg00Tonn.py /home/mpetrick/Pictures/

# -------------------------------------------

# example call
#     ~/repos/DevNotes/BeenThereSeenThat/20240724_Einfuehrung_in_Microservices    master *1  python ~/repos/codingWithGPT/changeScreenshotNamesIntoImg00Tonn.py .                                                                                                               ✔
# path_arg: .
# Screenshot_20240724_150241.png -> img00.png
# Screenshot_20240724_150308.png -> img01.png
# Screenshot_20240724_150315.png -> img02.png
# Screenshot_20240724_150509.png -> img03.png
# Screenshot_20240724_150714.png -> img04.png
# Screenshot_20240724_151100.png -> img05.png
# Screenshot_20240724_151139.png -> img06.png
# Screenshot_20240724_151356.png -> img07.png
# ![](img00.png)
# ![](img01.png)
# ![](img02.png)
# ![](img03.png)
# ![](img04.png)
# ![](img05.png)
# ![](img06.png)
# ![](img07.png)
#     ~/repos/DevNotes/BeenThereSeenThat/20240724_Einfuehrung_in_Microservices    master *1 
