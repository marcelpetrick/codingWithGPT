# Hackerman GUI

The Hackerman GUI is a PyQt5-based graphical user interface that allows users to input prompts, process them, and display the results in a scrolling view. It provides a futuristic-themed interface with neon and violet colors.

## Installation and Configuration

To run the Hackerman GUI, you need to have Python 3.x installed on your system. Additionally, you'll need to install the required Python dependencies listed in the `requirements.txt` file. You can install them using the following command:

`pip install -r requirements.txt`

## How to Run

To run the Hackerman GUI, execute the following command:

`python main.py`


## Usage

1. Enter your prompt in the input field.
2. Click the "Go" button to process the prompt.
3. The program will display a busy animation and block the input field and button while processing the prompt.
4. Once the processing is complete, the result will be shown in the scrolling view.
5. The result will be formatted using Markdown, with the prompt displayed first, followed by the processed result.
6. The program will update the result view for each new prompt, adding a separator line between each prompt and result.
7. You can scroll down to view the latest results.
8. The program also displays three arbitrary statistics in the footer section.

## Expected Result

The expected result of running the Hackerman GUI is a responsive interface where you can input prompts, process them, and view the formatted results. The program provides a visually appealing interface and updates the result view as new prompts are processed. The result is formatted using Markdown, making it easy to read and understand.
