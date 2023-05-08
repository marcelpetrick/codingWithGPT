# I have a webp file with animations fo 30 frames. this file should be split into single frames and stored as GIF in
# the same folder. the resolution should not be changed, colors should be kept as well. the frames should be numbered
# frame00.gif to frameXX.gif. The script shall be written in python and use a path to a webp-file as input. document
# the code with sphinx as well.

# pip install pillow

from PIL import Image
import os
import sys

def extract_frames(input_path):
    """
    Extract frames from an animated webp file and save them as GIF files.

    :param input_path: str
        Path to the webp file.
    :return: None
    """
    try:
        im = Image.open(input_path)
        base_dir, _ = os.path.splitext(input_path)
        os.makedirs(base_dir, exist_ok=True)

        i = 0
        while True:
            im.seek(i)
            frame_path = os.path.join(base_dir, f"frame{i:02d}.gif")
            im.save(frame_path, "GIF", save_all=True)
            i += 1
    except EOFError:
        # End of the animation
        pass
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python webpToGif.py path/to/your/webp/file.webp")
        sys.exit(1)

    input_path = sys.argv[1]
    extract_frames(input_path)
