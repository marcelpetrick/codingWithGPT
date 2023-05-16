# write me a python script which takes a path to a folder as input. it should collect all the names of the folders inside that directory and parse them. which means to take the prefix of the name, which is the date in the form YYYYMMDD. then that data should be used to generate a bar chart with maybe matplotlib. there should be bars for each month according to the amount of folders which refer to that month. and the file should be saved as output.png

import os
import re
import collections
import matplotlib.pyplot as plt
import datetime


def parse_dates_from_folder_names(folder_path):
    date_regex = r"(\d{8})"
    date_list = []

    for folder in os.listdir(folder_path):
        match = re.search(date_regex, folder)
        if match:
            date_list.append(match.group(0)[:6])  # taking only year and month

    return date_list


def count_dates(date_list):
    return collections.Counter(date_list)


def plot_date_counts(date_counts):
    # sort by date
    sorted_counts = {k: v for k, v in sorted(date_counts.items())}

    dates = [datetime.datetime.strptime(date, '%Y%m') for date in sorted_counts.keys()]
    counts = sorted_counts.values()

    plt.figure(figsize=(10, 6))
    plt.bar(dates, counts)
    plt.xlabel('Month')
    plt.ylabel('Number of folders')
    plt.title('Number of folders per month')
    plt.savefig('output.png')


def main(folder_path):
    date_list = parse_dates_from_folder_names(folder_path)
    date_counts = count_dates(date_list)
    plot_date_counts(date_counts)


if __name__ == "__main__":
    main("/home/mpetrick/repos/DevNotes/BeenThereSeenThat/")  # replace with your directory
