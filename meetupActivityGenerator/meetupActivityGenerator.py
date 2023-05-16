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

# ok. already good, but make  the description on the horizontal scale a bit better. each month should have a tick. and a rotated text for "021-05", "021-06" and so on.
# also limit the amount of items for the vertical axis to the maxmium height +1. Not soo much free whitespace.
# at last: make the bars a bit wider. and color them red. red rectangles.
def plot_date_counts(date_counts):
    # sort by date
    sorted_counts = {k: v for k, v in sorted(date_counts.items())}

    dates = [datetime.datetime.strptime(date, '%Y%m') for date in sorted_counts.keys()]
    counts = list(sorted_counts.values())

    plt.figure(figsize=(10, 6))

    # Create wider, red bars
    plt.bar(dates, counts, color='red', width=20)

    # Set y-axis limit
    plt.ylim(0, max(counts) + 1)

    # Set x-axis labels rotated
    plt.xticks(dates, [date.strftime('%Y-%m') for date in dates], rotation='vertical')

    plt.xlabel('Month')
    plt.ylabel('Number of visited meetups')
    plt.title('Number of visited meetups per month')
    plt.tight_layout()  # ensures that the x-labels are fully visible
    plt.savefig('output.png')


def main(folder_path):
    date_list = parse_dates_from_folder_names(folder_path)
    date_counts = count_dates(date_list)
    plot_date_counts(date_counts)


if __name__ == "__main__":
    main("/home/mpetrick/repos/DevNotes/BeenThereSeenThat/")
