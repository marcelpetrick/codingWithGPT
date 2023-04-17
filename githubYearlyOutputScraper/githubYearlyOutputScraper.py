# Plan is to make a script, which renders my own github-profile and then screenshots the part of the commit-graph.
# Doing this for every of the available years and saving this as PNG. Plan is to convert them later to a GIF.
# Start 20230417_2245

# pip install pillow
# pip install selenium
import os
import time
from selenium import webdriver
from PIL import Image
from selenium.webdriver.firefox.options import Options

# Set the path to the geckodriver
#gecko_driver_path = os.path.join(os.getcwd(), "geckodriver")
gecko_driver_path = "C:\\geckodriver\\geckodriver.exe"

# Set up the browser
options = Options()
binary = r'C:\Users\mpetrick\AppData\Local\Microsoft\WindowsApps\firefox.exe'
options.binary_location = binary
options.headless = True

# problem with FF path: cmd > where /R C:\ firefox.exe
# C:\Users\mpetrick>where /R C:\ firefox.exe
# C:\Users\mpetrick\AppData\Local\Microsoft\WindowsApps\firefox.exe
#options.binary_location = "C:\\Users\\mpetrick\\AppData\\Local\\Microsoft\\WindowsApps\\Mozilla.Firefox_n80bbvh6b1yt2\\firefox.exe"
# Initialize the WebDriver
browser = webdriver.Firefox(executable_path=gecko_driver_path, options=options)
# fails here with
# "selenium.common.exceptions.InvalidArgumentException: Message: binary is not a Firefox executable" ..
# after lots or reading and checking and trying ..
# The Windows app binary for Firefox is a different executable than the regular Firefox installation. While the Windows app version of Firefox uses the same rendering engine and shares most features with the regular Firefox, it's packaged and installed differently, which can cause compatibility issues with certain tools, like Selenium.
browser.set_window_size(1920, 1080)

# Navigate to the GitHub profile
url = "https://github.com/marcelpetrick/"
browser.get(url)

# Wait for the page to load
time.sleep(5)

# Find the commit graph element
commit_graph = browser.find_element_by_css_selector("div.js-yearly-contributions")

# Screenshot the commit graph
commit_graph.screenshot("commit_graph.png")

# Close the browser
browser.quit()

# Open the image and crop if necessary
image = Image.open("commit_graph.png")
image.show()

# Save the final image
image.save("commit_graph_cropped.png")
