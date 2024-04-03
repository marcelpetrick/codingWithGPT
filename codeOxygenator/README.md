# codeOxygenator

`codeOxygenator` is a powerful automation tool designed to streamline the documentation process of coding projects. By leveraging the capabilities of GPT-4, this tool analyzes your source code and automatically decorates it with Doxygen comments. It focuses on enriching classes, methods, and public interfaces with insightful, accurate, and helpful documentation comments, saving developers countless hours of manual work.

## Features

- **Automated Documentation**: Automatically adds Doxygen comments to your code, covering classes, methods, and public interfaces.
- **GPT-4 Integration**: Utilizes the latest GPT-4 model to ensure high-quality documentation that understands the context of your code.
- **Supports Multiple Languages**: Initially supports `C++` and `Python` files, with plans to extend support for more programming languages.
- **Flexible and Easy to Use**: Simply run the script with your desired directory and file types, and watch as your code is documented.

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.x
- Requests library for Python (`pip install requests`)
- An active OpenAI API key set in your environment variables as `OPENAI_API_KEY`.

### Installation

Clone this repository to your local machine to get started with `codeOxygenator`:

```bash
git clone https://github.com/your-repository/codeOxygenator.git
cd codeOxygenator
```

### Usage

To start using **codeOxygenator**, navigate to the cloned directory and run:

```bash
python codeOxygenator.py --path=<path-to-your-code-directory> --type=<comma-separated-file-extensions>
```
For example, to document C++ and Header files in the test/ directory, run:

```bash
python codeOxygenator.py --path=test/ --type=cpp,h
```

### How It Works

**codeOxygenator** consists of two main components:

* File Finder Script: Scans the specified directory for files with the given extensions and prepares them for decoration.
* AutoDecorator Class: Sends the content of each file to the GPT-4 API and decorates them with Doxygen comments based on the model's suggestions.

## License

**codeOxygenator** is released under the GPL v3 license. Feel free to use, modify, and distribute, as long as you
keep the spirit of open source alive.

## Contact

For bugs, feature requests, or just to say hi, reach out to Marcel Petrick
at [mail@marcelpetrick.it](mailto:mail@marcelpetrick.it).
