import re
from datetime import datetime

def extract_dates(line):
    dates = []
    matches = re.findall(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z', line)
    for match in matches:
        dates.append(datetime.strptime(match, '%Y-%m-%dT%H:%M:%S.%fZ'))
    return dates

def find_earliest_and_latest_dates(file_path):
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
    file_path = 'collectedUpdate3Tickets_20230808_1736.txt'
    earliest_date, latest_date = find_earliest_and_latest_dates(file_path)
    print(f'Earliest date: {earliest_date}')
    print(f'Latest date: {latest_date}')

if __name__ == "__main__":
    main()
