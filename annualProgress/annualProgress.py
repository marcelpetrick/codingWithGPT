import argparse
from datetime import datetime
import unittest

# Function to check leap year
def is_leap_year(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

# Function to calculate year progress
def year_progress(today):
    start_of_year = datetime(today.year, 1, 1)
    end_of_year = datetime(today.year + 1, 1, 1)
    total_days = (end_of_year - start_of_year).days
    days_passed = (today - start_of_year).days
    return (days_passed / total_days) * 100

class TestYearProgress(unittest.TestCase):

    def test_january_3rd(self):
        # January 3rd should be roughly 1% of the year, slightly less in a leap year
        self.assertAlmostEqual(year_progress(datetime(2023, 1, 3)), 1, delta=0.5)
        self.assertAlmostEqual(year_progress(datetime(2024, 1, 3)), 1, delta=0.5)

    def test_leap_year(self):
        # Checking February 29 in a leap year
        self.assertAlmostEqual(year_progress(datetime(2024, 2, 29)), 100 * 59 / 366, delta=0.01)

    def test_non_leap_year(self):
        # Checking February 28 in a non-leap year
        self.assertAlmostEqual(year_progress(datetime(2023, 2, 28)), 100 * 58 / 365, delta=0.01)

# Main function to handle command line arguments
def main():
    parser = argparse.ArgumentParser(description="Calculate the annual progress.")
    parser.add_argument('-tests', action='store_true', help='Run unit tests')
    parser.add_argument('-date', type=str, help='Calculate progress for a given date (format DD.MM.)')
    args = parser.parse_args()

    if args.tests:
        unittest.main(argv=['first-arg-is-ignored'], exit=False)
    elif args.date:
        day, month = map(int, args.date.split('.'))
        specified_date = datetime(datetime.now().year, month, day)
        print(f"{year_progress(specified_date):.1f}%")
    else:
        print(f"{year_progress(datetime.now()):.1f}%")

if __name__ == "__main__":
    main()
