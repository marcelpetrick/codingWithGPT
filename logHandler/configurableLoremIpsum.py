# Write me a python program, which generates output for stdout. It should be called "configurableLoremIpsum". Startable with "python configurableLoremIpsum.py --rate==10 --line==1024" and then print out 1024 characters every 10 seconds. Until interrupted. if no parameters are given, then it should print out the help page.
#
# write program with class and sphinx documentation and comments. also take care of pep8.

import argparse
import time

class ConfigurableLoremIpsum:
    """Class to generate and output Lorem Ipsum text at a configurable rate and length.

    Attributes:
        rate (int): The rate at which the text should be output, in seconds.
        line_length (int): The length of the text to be generated, in characters.

    Methods:
        generate_text(): Generates Lorem Ipsum text of the specified length.
        output_text(): Outputs the generated text at the specified rate.
    """

    def __init__(self, rate, line_length):
        """Initializes ConfigurableLoremIpsum with the specified rate and line_length."""
        self.rate = rate
        self.line_length = line_length

    def generate_text(self):
        """Generates Lorem Ipsum text of the specified length.

        Returns:
            str: The generated Lorem Ipsum text.
        """
        lorem_ipsum = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
                       "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.")
        return (lorem_ipsum * (self.line_length // len(lorem_ipsum) + 1))[:self.line_length]

    def output_text(self):
        """Outputs the generated text at the specified rate."""
        while True:
            print(self.generate_text())
            time.sleep(self.rate)

def main():
    parser = argparse.ArgumentParser(description="Generate and output Lorem Ipsum text at a configurable rate and length.")
    parser.add_argument('--rate', type=int, help='Rate at which text should be output, in seconds.', default=10)
    parser.add_argument('--line', type=int, help='Length of the text to be generated, in characters.', default=1024)

    args = parser.parse_args()
    lorem_generator = ConfigurableLoremIpsum(args.rate, args.line)
    lorem_generator.output_text()

if __name__ == "__main__":
    main()
