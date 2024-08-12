# Pygame Browser Test

**change of plans**: pygbag and pygame did not work well, because pygame can't draw, so tried pyodide ... this works .. so just run the `index.htm` (serving by Github pages is still wip) manually in your browser.

Check this: [on Github pages](https://marcelpetrick.github.io/codingWithGPT/pythonBrowserTest/)

------------------------------------

## Project Overview

This project is a simple test to demonstrate running a Pygame application in a web browser using `pygbag`. The goal is to explore the capabilities of Pygame when deployed as a web application. This project is intended for educational and experimental purposes.

## Setup Instructions

### 1. Clone the Repository

First, clone this repository to your local machine:

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### 2. Install Dependencies

Set up a virtual environment and install the required dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Build the Project

Use `pygbag` to build the Pygame project for the web:

```bash
pygbag my_game
```

This will generate the necessary files in the `build/web` directory.

### 4. Serve the Project Locally

After building, you can serve the project using Python's built-in HTTP server:

```bash
cd my_game/build/web
python3 -m http.server
```

Navigate to `http://localhost:8000` in your web browser to view the game.

## Author

This project was created by mail@marcelpetrick.it.  
It serves as a test and demonstration of running `pygame` applications in the browser.

## Purpose

The intention of this project is to test and explore how Pygame can be deployed as a web application using `pygbag`. This is a proof of concept and not intended for production use.
