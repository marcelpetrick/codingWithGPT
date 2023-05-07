# markdownDayGenerator

import sys
from calendar import monthrange
from datetime import datetime

def generate_dates(year_month):
    """
    Generates a list of dates in reverse order for the specified month.

    Args:
        year_month (str): A string representing the year and month in the format 'YYYYMM'.

    Returns:
        None
    """
    year = int(year_month[:4])
    month = int(year_month[4:])

    last_day_of_month = monthrange(year, month)[1]

    for day in reversed(range(1, last_day_of_month + 1)):
        date = datetime(year, month, day).strftime('%Y%m%d ')
        print(f"* {date}")

def get_current_year_month():
    """
    Returns the current year and month as a string in the format 'YYYYMM'.

    Returns:
        str: The current year and month in the format 'YYYYMM'.
    """
    return datetime.now().strftime('%Y%m')

if __name__ == "__main__":
    if len(sys.argv) == 2:
        year_month = sys.argv[1]
    else:
        year_month = get_current_year_month()

    generate_dates(year_month)
