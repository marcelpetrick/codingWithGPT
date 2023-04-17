# Plan is to make a script, which renders my own github-profile and then screenshots the part of the commit-graph.
# Doing this for every of the available years and saving this as PNG. Plan is to convert them later to a GIF.
# Start 20230417_2245

# pip install pillow
# pip install selenium
import os
import time
from selenium import webdriver
from PIL import Image

# Set the path to the Edge WebDriver
edge_driver_path = os.path.join(os.getcwd(), "msedgedriver.exe")

# Set up the browser
options = webdriver.EdgeOptions()
options.use_chromium = True  # This line is necessary for Edge Chromium
options.headless = True

# Initialize the WebDriver
browser = webdriver.Edge(executable_path=edge_driver_path, options=options)
browser.set_window_size(1920, 1080)

# Navigate to the GitHub profile
url = "https://github.com/marcelpetrick/"
browser.get(url)

# Wait for the page to load
time.sleep(5)

# Find the commit graph element
from selenium.webdriver.common.by import By
commit_graph = browser.find_element(By.CSS_SELECTOR, "div.js-yearly-contributions") # Code needed to be replaced, because deprecated

# Screenshot the commit graph
commit_graph.screenshot("commit_graph.png")

# Close the browser
browser.quit()

# Open the image and crop if necessary
image = Image.open("commit_graph.png")
image.show()

# Save the final image
image.save("commit_graph_cropped.png")
