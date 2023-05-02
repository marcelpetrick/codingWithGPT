# pip install scikit-learn
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

def convert_to_red_black_white_kmeans(image_path, output_path):
    # Open the input image
    image = Image.open(image_path)

    # Convert the image to RGB mode
    image = image.convert('RGB')

    # Convert the image to a numpy array and reshape it to a 2D array
    image_data = np.array(image)
    image_data = image_data.reshape(-1, 3)

    # Define the target palette (red, black, and white)
    target_palette = np.array([[255, 0, 0], [0, 0, 0], [255, 255, 255]])

    # Apply k-means clustering
    kmeans = KMeans(n_clusters=3, init=target_palette, random_state=42, n_init=1)
    kmeans.fit(image_data)
    labels = kmeans.predict(image_data)
    centroids = kmeans.cluster_centers_

    # Replace each pixel color with the corresponding cluster's centroid color
    new_image_data = centroids[labels].astype(np.uint8).reshape(image_data.shape)

    # Create a new image with the converted colors
    new_image = Image.fromarray(new_image_data, mode='RGB')

    # Save the converted image as a PNG
    new_image.save(output_path, 'PNG')

# Example usage:
input_image_path = 'path/to/your/input/image.jpg'
output_image_path = 'path/to/your/output/image.png'
convert_to_red_black_white_kmeans(input_image_path, output_image_path)
