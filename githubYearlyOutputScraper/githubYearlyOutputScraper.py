# Plan is to make a script, which renders my own github-profile and then screenshots the part of the commit-graph.
# Doing this for every of the available years and saving this as PNG. Plan is to convert them later to a GIF.
# Start 20230417_2245 - End 20230417_2330
# Start 20230418_1840 - End 20230418_1910
# Start 20230418_2335 - End 20230419_0010
# sum: 110 min

# How to get those via pip?
# pip install pillow
# pip install selenium

# I have a URL called "https://github.com/marcelpetrick?tab=overview&from=2022-12-01&to=2022-12-31" . Generate me
# code which is usable for all years from 2015 to 2023. Returnvalue should be a list of all urls
def urlCreator():
    def generate_github_urls(username, start_year, end_year):
        base_url = "https://github.com/{username}?tab=overview&from={year}-01-01&to={year}-12-31"
        urlsDict = dict()

        for year in range(start_year, end_year + 1):
            url = base_url.format(username=username, year=year)
            #urls.append(url)
            urlsDict[year] = url

        return urlsDict

    # Generate URLs for the years 2015 to 2023
    username = "marcelpetrick"
    start_year = 2015
    end_year = 2023
    urls = generate_github_urls(username, start_year, end_year)
    print(urls)
    return urls

#urlCreator()

#----------------------------------------------------------------------------------------------------------------
# Regenerated the prompt to use Microsoft Edge, because the geckodriver did not work with the Firefox coming from those
# Windows-Apps - no proper executable. With the limited admin rights on this machine, I choose another path ..
def imageGetter():
    import os
    import time
    from selenium import webdriver
    from selenium.webdriver.common.by import By

    # Set the path to the Edge WebDriver
    edge_driver_path = os.path.join(os.getcwd(), "msedgedriver.exe") # put this to the main partition, no need to adjust

    # Set up the browser
    options = webdriver.EdgeOptions()
    options.use_chromium = True  # This line is necessary for Edge Chromium
    options.headless = True

    # Initialize the WebDriver
    browser = webdriver.Edge(executable_path=edge_driver_path, options=options)
    browser.set_window_size(1920, 1080)

    # Navigate to the GitHub profile
    #url = "https://github.com/marcelpetrick/" # set my own repo

    # new code to loop over the urls - manually written, no clue how to query ChatGPT
    urlsDict = urlCreator()
    for year, url in urlsDict.items():
        print(f"processing {year}")
        browser.get(url)

        # Wait for the page to load
        time.sleep(2) # TODO really necessary? Maybe reduce this

        # Find the commit graph element - had to be adjusted due to deprecation. Result from the prompt was not working, pre-2022!
        commit_graph = browser.find_element(By.CSS_SELECTOR, "div.js-yearly-contributions") # Code needed to be replaced, because deprecated

        # Screenshot the commit graph
        commit_graph.screenshot(f"output/commit_graph{year}.png")

    # Close the browser
    browser.quit()

#----------------------------------------------------------------------------------------------------------------
# Generate me code which puts all the PNG files it has found in the subfolder "output" into a single looped gif. The duration for each frame fo the gif should be 0.1 second.
def imageCombiner():
    import os
    from PIL import Image

    # Define the input and output paths
    input_folder = "output"
    output_file = "looped_gif.gif"

    # Get a list of all PNG files in the input folder
    png_files = [f for f in os.listdir(input_folder) if f.endswith(".png")]
    # "How to sort a list named png_files descending?"
    sorted_png_files = sorted(png_files, reverse=True)

    # Open the images and store them in a list
    images = [Image.open(os.path.join(input_folder, f)) for f in sorted_png_files]

    # Save the images as a single looped GIF
    images[0].save(
        output_file,
        save_all=True,
        append_images=images[1:],
        duration=500,  # Duration in milliseconds, 100 ms = 0.1 second # increased to 500
        loop=0,  # 0 means loop indefinitely
    )

#----------------------------------------------------------------------------------------------------------------
# final calls
imageGetter()
imageCombiner()
