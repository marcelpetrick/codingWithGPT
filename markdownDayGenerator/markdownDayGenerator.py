# markdownDayGenerator
#
#

import sys
from calendar import monthrange
from datetime import datetime

def generate_dates(year_month):
    year = int(year_month[:4])
    month = int(year_month[4:])

    last_day_of_month = monthrange(year, month)[1]

    for day in reversed(range(1, last_day_of_month + 1)):
        date = datetime(year, month, day).strftime('%Y%m%d')
        print(f"* {date} ")

if __name__ == "__main__":
    if len(sys.argv) == 2:
        year_month = sys.argv[1]
        generate_dates(year_month)
    else:
        print("Usage: python3 dayGenerator.py <year_month>")
