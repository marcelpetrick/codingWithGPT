# pip install scikit-learn
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

def load_image_and_prepare_array(image_path):
    try:
        # Open the input image
        image = Image.open(image_path)

        # Convert the image to RGB mode
        image = image.convert('RGB')

        # Convert the image to a numpy array and reshape it to a 2D array
        image_data = np.array(image)
        image_data = image_data.reshape(-1, 3)

        return image, image_data

    except IOError:
        print(f"Error: Cannot open the image file at {image_path}")
        return None, None
    except ValueError as e:
        print(f"Error: {e}")
        return None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def process_and_save_image(image_data, output_path):
    try:
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
        print(f"Image converted successfully and saved to {output_path}")

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

# Example usage:
input_image_path = 'farbkreis.jpg'
output_image_path = 'werni_out.png'
image, image_data = load_image_and_prepare_array(input_image_path)
print("prepped image :)")
if image_data is not None:
    process_and_save_image(image_data, output_image_path)
