import subprocess
import datetime


def get_current_day_of_year():
    """Get the current day of the year using the `date +%j` bash command."""
    result = subprocess.run(['date', '+%j'], capture_output=True, text=True, check=True)
    return int(result.stdout.strip())


def is_leap_year(year):
    """Check whether a given year is a leap year."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def annual_progress_percentage(day_of_year, year=None):
    """Calculate the percentage of the year that has passed."""
    if year is None:
        year = datetime.datetime.now().year
    total_days = 366 if is_leap_year(year) else 365
    percentage = (day_of_year / total_days) * 100
    return int(percentage)


def main():
    day_of_year = get_current_day_of_year()
    year = datetime.datetime.now().year
    print(annual_progress_percentage(day_of_year, year))


if __name__ == '__main__':
    main()
