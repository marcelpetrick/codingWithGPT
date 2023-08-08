import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as patches
from datetime import datetime
import ast
import re

def extract_tickets_from_file(file_path):
    """Extracts ticket information from a given text file."""
    tickets = []
    with open(file_path, 'r') as file:
        for line in file:
            ticket = ast.literal_eval(line.strip())
            tickets.append(ticket)
    return tickets

def plot_tickets(tickets, start_date, end_date):
    """Plots tickets on a timeline using specified start and end dates."""
    fig, ax = plt.subplots(figsize=(15, len(tickets) * 0.5))

    # Increase the left margin to accommodate text
    plt.subplots_adjust(left=0.5)

    ax.set_xlim(start_date, end_date)
    ax.set_ylim(0, len(tickets))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    plt.title(f'Tickets from {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
    plt.yticks(range(len(tickets)), [""] * len(tickets))  # Empty y-ticks

    colors = ['red', 'green', 'yellow', 'orange', 'purple']

    for idx, ticket in enumerate(tickets):
        y_value = idx
        created_date = datetime.strptime(ticket['Created Date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        resolved_date = datetime.strptime(ticket['Resolved Date'], '%Y-%m-%dT%H:%M:%S.%fZ') if ticket['Resolved Date'] else end_date
        closed_date = datetime.strptime(ticket['Closed Date'], '%Y-%m-%dT%H:%M:%S.%fZ') if ticket['Closed Date'] else end_date

        # Draw the rectangle for the ticket
        rect = patches.Rectangle((mdates.date2num(created_date), y_value - 0.2), mdates.date2num(resolved_date or closed_date) - mdates.date2num(created_date), 0.4,
                                 facecolor=colors[idx % len(colors)], edgecolor='black')
        ax.add_patch(rect)

        # Add the ticket details
        title_ellipsed = (ticket['Title'][:30] + '...') if len(ticket['Title']) > 30 else ticket['Title']
        ax.text(mdates.date2num(start_date) - 100, y_value, f"ID: {ticket['ID']} | Type: {ticket['Work Item Type']} | Title: {title_ellipsed}",
                verticalalignment='center', horizontalalignment='right', fontsize=8)

    plt.gca().invert_yaxis()
    plt.savefig('tickets_plot.png')
    #plt.show()


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
    file_path = 'collectedUpdate3Tickets_20230808_1736.txt'
    tickets = extract_tickets_from_file(file_path)

    # Find the global earliest and latest dates
    all_dates = [datetime.strptime(ticket['Created Date'], '%Y-%m-%dT%H:%M:%S.%fZ') for ticket in tickets]
    all_dates += [datetime.strptime(ticket['Resolved Date'], '%Y-%m-%dT%H:%M:%S.%fZ') for ticket in tickets if ticket['Resolved Date']]
    all_dates += [datetime.strptime(ticket['Closed Date'], '%Y-%m-%dT%H:%M:%S.%fZ') for ticket in tickets if ticket['Closed Date']]
    earliest_date = min(all_dates)
    latest_date = max(all_dates)

    print(f'Earliest date: {earliest_date.strftime("%Y-%m-%d %H:%M")}')
    print(f'Latest date: {latest_date.strftime("%Y-%m-%d %H:%M")}')

    plot_tickets(tickets, earliest_date, latest_date)


if __name__ == "__main__":
    main()
