# create me a python script which can generate images with size 960x768. they are stored as lossless PNG. the whole background should be white. Place two rows of 10 squares. for the first row the squares have in the beginning a color-value for red of 0, then 1 * 255/10, then 2*/255/10, then 3*255/10 and so on. So the last square is fully red.
# the second row of squares does the same for black. first almost white, then a bit black, then more black .. until the last one is fully black.

from PIL import Image, ImageDraw

# Image dimensions
width, height = 960, 768

# Create a new image with a white background
image = Image.new("RGB", (width, height), (255, 255, 255))
draw = ImageDraw.Draw(image)

# Square size
square_size = min(width // 10, height // 2)

# Draw the first row of squares (red)
for i in range(10):
    red_value = int(i * 255 / 10)
    color = (red_value, 0, 0)
    draw.rectangle([(i * square_size, 0), ((i + 1) * square_size, square_size)], fill=color)

# Draw the second row of squares (black)
for i in range(10):
    gray_value = 255 - int(i * 255 / 10)
    color = (gray_value, gray_value, gray_value)
    draw.rectangle([(i * square_size, square_size), ((i + 1) * square_size, 2 * square_size)], fill=color)

# Save the image as a lossless PNG
image.save("generated_image.png", "PNG")
