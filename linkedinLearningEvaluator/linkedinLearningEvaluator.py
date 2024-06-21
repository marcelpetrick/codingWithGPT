# linkedinLearningEvaluator
# ingest a given file (as first param from command line). default shall be "learningHistory.txt". parse the file for all titles and also extract the run time length. normalize the values to minutes.
# print then a list of tuples "title: time". als give me the sum of all times in minutes as output to the commandline (stdout). add for each step some status output like "reading data", "processing data", "preparing accumulation", "printing".
# make the code PEP8-compatible and robust and well documented (Sphynx.) assume you are guide van rossum, the python master mind. Write pythonic code!
# let me give you some example text for the structure of the input data:

# ```
# Course: Difficult Situations: Solutions for Managers
# 1h 6m
# Difficult Situations: Solutions for Managers
# COURSE Course
#
#     LinkedIn
#     By: Todd Dewett and Sara Canaday
#     Updated Jun 2020
#
# Completed 6/20/2024
#
# Course: Delivering Employee Feedback
# 27m
# Delivering Employee Feedback
# COURSE Course
#
#     LinkedIn
#     By: Todd Dewett
#     May 2019
#
# Completed 6/18/2024
#
# Course: Social Success at Work
# 18m
# Social Success at Work
# COURSE Course
#
#     LinkedIn
#     By: Todd Dewett
#     Jul 2019
#
# Completed 6/17/2024
# ```

import re
import sys


def parse_input_file(filename):
    """
    Parses the input file to extract course titles and durations.

    Args:
        filename (str): The name of the file to read.

    Returns:
        list: A list of tuples containing course titles and their durations in minutes.
    """
    print("Reading data...")

    with open(filename, 'r') as file:
        content = file.read()

    print("Processing data...")

    courses = re.findall(r'Course: (.*?)\n(\d+h \d+m|\d+m|\d+h)', content)

    course_list = []
    for course in courses:
        title, duration = course
        hours = 0
        minutes = 0
        if 'h' in duration:
            hours = int(re.search(r'(\d+)h', duration).group(1))
        if 'm' in duration:
            minutes = int(re.search(r'(\d+)m', duration).group(1))
        total_minutes = hours * 60 + minutes
        course_list.append((title, total_minutes))

    return course_list


def calculate_total_time(course_list):
    """
    Calculates the total duration of all courses in minutes.

    Args:
        course_list (list): A list of tuples containing course titles and their durations in minutes.

    Returns:
        int: The total duration of all courses in minutes.
    """
    print("Preparing accumulation...")

    total_time = sum(time for _, time in course_list)
    return total_time


def main(filename='learningHistory.txt'):
    """
    Main function to process the input file and print the course titles and durations.

    Args:
        filename (str, optional): The name of the file to read. Defaults to 'learningHistory.txt'.
    """
    course_list = parse_input_file(filename)

    print("Printing data...")
    print("------------------------------")
    for title, time in course_list:
        print(f"{title}: {time} minutes")
    print("------------------------------")
    total_time = calculate_total_time(course_list)
    print(f"\nTotal time: {total_time} minutes")


if __name__ == '__main__':
    filename = sys.argv[1] if len(sys.argv) > 1 else 'learningHistory.txt'
    main(filename)


#---------------
# Not bad for seven minutes of "coding":
#
# ..
# Cert Prep: Scrum Master: 86 minutes
# Scrum: Advanced (2017): 62 minutes
# Refresh Your Workplace Social Skills: 46 minutes
# Building Your Visibility as a Leader: 39 minutes
# The Six Morning Habits of High Performers: 23 minutes
# ------------------------------
# Preparing accumulation...
#
# Total time: 9009 minutes
# (venv) [mpetrick@mpetrick-precision3551 linkedinLearningEvaluator]$