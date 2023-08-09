import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as patches
from datetime import datetime
import ast
import re
import glob
import os


def extract_tickets_from_file(file_path):
    """Extracts ticket information from a given text file.

    :param file_path: Path to the text file containing ticket information.
    :return: A list of dictionaries, each representing a ticket.
    """
    tickets = []
    with open(file_path, 'r') as file:
        for line in file:
            ticket = ast.literal_eval(line.strip())
            tickets.append(ticket)
    return tickets


def plot_tickets(tickets, start_date, end_date, result_file_name):
    """Plots tickets on a timeline using specified start and end dates.

    :param tickets: A list of dictionaries, each representing a ticket.
    :param start_date: The start date for the timeline.
    :param end_date: The end date for the timeline.
    :param result_file_name: The name of the resulting plot file.
    """
    fig, ax = plt.subplots(figsize=(15, len(tickets) * 0.5))
    plt.subplots_adjust(left=0.5)

    ax.set_xlim(start_date, end_date)
    ax.set_ylim(0, len(tickets))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    plt.title(f'Tickets from {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
    plt.yticks(range(len(tickets)), [""] * len(tickets))  # Empty y-ticks

    # Color mapping based on ticket type
    type_colors = {
        'Feature': 'purple',
        'Task': 'yellow',
        'User Story': 'yellow',
        'Bug': 'red',
    }

    # Add vertical dashed line at specified date
    implementation_date = datetime.strptime('2023-06-01', '%Y-%m-%d')
    ax.axvline(implementation_date, linestyle='--', color='black', lw=1)
    ax.text(implementation_date, len(tickets) - 1, 'start of implementation', rotation=90, verticalalignment='bottom', fontsize=8)

    for idx, ticket in enumerate(tickets):
        y_value = idx
        created_date = datetime.strptime(ticket['Created Date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        resolved_date = datetime.strptime(ticket['Resolved Date'], '%Y-%m-%dT%H:%M:%S.%fZ') if ticket['Resolved Date'] else end_date
        closed_date = datetime.strptime(ticket['Closed Date'], '%Y-%m-%dT%H:%M:%S.%fZ') if ticket['Closed Date'] else end_date

        # Select the color based on ticket type
        color = type_colors.get(ticket['Work Item Type'], 'gray')  # Default to gray if type is not recognized

        # Draw the rectangle for the ticket
        rect = patches.Rectangle((mdates.date2num(created_date), y_value - 0.2), mdates.date2num(resolved_date or closed_date) - mdates.date2num(created_date), 0.4,
                                 facecolor=color, edgecolor='black')
        ax.add_patch(rect)

        # Add the ticket details
        title_ellipsed = (ticket['Title'][:30] + '...') if len(ticket['Title']) > 30 else ticket['Title']
        ax.text(mdates.date2num(start_date) - 100, y_value, f"ID: {ticket['ID']} | Type: {ticket['Work Item Type']} | Title: {title_ellipsed}",
                verticalalignment='center', horizontalalignment='right', fontsize=8)

    plt.gca().invert_yaxis()
    plt.savefig(result_file_name)  # Save the plot with the specified file name


def extract_dates(line):
    """Extracts dates from a given line.

    :param line: A string containing dates in a specific format.
    :return: A list of datetime objects representing the extracted dates.
    """
    dates = []
    matches = re.findall(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z', line)
    for match in matches:
        dates.append(datetime.strptime(match, '%Y-%m-%dT%H:%M:%S.%fZ'))
    return dates


def find_earliest_and_latest_dates(file_path):
    """Finds the earliest and latest dates from a given text file.

    :param file_path: Path to the text file containing dates.
    :return: Strings representing the earliest and latest dates in 'YYYY-MM-DD hh:mm' format.
    """
    earliest_date = None
    latest_date = None
    with open(file_path, 'r') as file:
        for line in file:
            dates = extract_dates(line)
            for date in dates:
                if earliest_date is None or date < earliest_date:
                    earliest_date = date
                if latest_date is None or date > latest_date:
                    latest_date = date

    return earliest_date.strftime('%Y-%m-%d %H:%M') if earliest_date else None, latest_date.strftime('%Y-%m-%d %H:%M') if latest_date else None


def main():
    """Main function to extract ticket information, find global timescale, and plot tickets."""

    # Find all files matching the pattern and select the most recent one
    pattern = 'collectedUpdate3Tickets_*.txt'
    file_paths = glob.glob(pattern)
    file_path = max(file_paths, key=os.path.getctime) if file_paths else None
    print(f"Will operate on most recent file: {file_path}")

    if file_path is None:
        print("No matching files found.")
        return

    # Extracting the date-time part from the input file name
    date_time_part = re.search(r'(\d{8}_\d{4})', file_path).group(1) if file_path else ''
    result_file_name = f'tickets_plot_{date_time_part}.png'

    tickets = extract_tickets_from_file(file_path)

    # Find the global earliest and latest dates
    all_dates = [datetime.strptime(ticket['Created Date'], '%Y-%m-%dT%H:%M:%S.%fZ') for ticket in tickets]
    all_dates += [datetime.strptime(ticket['Resolved Date'], '%Y-%m-%dT%H:%M:%S.%fZ') for ticket in tickets if ticket['Resolved Date']]
    all_dates += [datetime.strptime(ticket['Closed Date'], '%Y-%m-%dT%H:%M:%S.%fZ') for ticket in tickets if ticket['Closed Date']]
    earliest_date = min(all_dates)
    latest_date = max(all_dates)

    print(f'Earliest date: {earliest_date.strftime("%Y-%m-%d %H:%M")}')
    print(f'Latest date: {latest_date.strftime("%Y-%m-%d %H:%M")}')

    plot_tickets(tickets, earliest_date, latest_date, result_file_name)  # Pass the result file name


if __name__ == "__main__":
    main()
