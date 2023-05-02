# pip install Pillow
from PIL import Image

# Algorithm:
# * load image file
# * resize while keeping aspect ratio and place it centered in a target-sized image (new background is white)
# * do the color-tone-mapping to red/black
# * save the output file
def convert_to_red_black_white(image_path, output_path, new_width=960, new_height=768):
    try:
        # Open the input image
        image = Image.open(image_path)

        # Calculate the aspect ratio
        aspect_ratio = float(image.width) / float(image.height)

        # Calculate new dimensions while maintaining the aspect ratio
        if aspect_ratio > 1:
            target_width = 960
            target_height = int(target_width / aspect_ratio)
        else:
            target_height = 768
            target_width = int(target_height * aspect_ratio)

        # Resize the image to the new dimensions using Lanczos resampling
        resized_image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)

        # Create a new blank image with the desired dimensions and a white background
        final_image = Image.new('RGB', (new_width, new_height), (255, 255, 255))

        # Calculate the position to paste the resized image onto the blank image at the center
        paste_position = ((new_width - target_width) // 2, (new_height - target_height) // 2)

        # Paste the resized image onto the blank image
        final_image.paste(resized_image, paste_position)

        # Convert the image to RGB mode
        image = final_image.convert('RGB')

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
