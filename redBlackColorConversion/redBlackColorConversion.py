# pip install scikit-learn
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import numpy as np
from PIL import Image

def convert_to_red_black_white(image_path, output_path):
    try:
        # Open the input image
        image = Image.open(image_path)

        # Convert the image to RGB mode
        image = image.convert('RGB')

        # Define the target palette (red, black, and white)
        target_palette = Image.new('P', (1, 1))
        target_palette.putpalette([255, 0, 0,  # Red
                                   0, 0, 0,    # Black
                                   255, 255, 255] + [0, 0, 0] * 253)  # White and padding

        # Quantize the image using the custom palette
        quantized_image = image.quantize(palette=target_palette, dither=Image.NONE)

        # Convert the quantized image back to RGB mode
        new_image = quantized_image.convert('RGB')

        # Save the converted image as a PNG
        new_image.save(output_path, 'PNG')
        print(f"Image converted successfully and saved to {output_path}")

    except IOError:
        print(f"Error: Cannot open the image file at {image_path}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

# Example usage:
input_image_path = 'werni.jpg'
output_image_path = 'werni_out.png'
convert_to_red_black_white(input_image_path, output_image_path)
input_image_path = 'farbkreis.jpg'
output_image_path = 'farbkreis_out.png'
convert_to_red_black_white(input_image_path, output_image_path)
