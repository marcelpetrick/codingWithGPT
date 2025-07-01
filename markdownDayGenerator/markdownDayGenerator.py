import sys
import argparse
import unittest
from calendar import monthrange
from datetime import datetime

def generate_dates(year_month):
    """
    Generates a list of dates in reverse order for the specified month.

    Args:
        year_month (str): A string representing the year and month in the format 'YYYYMM'.

    Returns:
        list[str]: List of strings formatted as '* YYYYMMDD '
    """
    year = int(year_month[:4])
    month = int(year_month[4:])

    last_day_of_month = monthrange(year, month)[1]

    return [f"* {datetime(year, month, day).strftime('%Y%m%d ')}" for day in reversed(range(1, last_day_of_month + 1))]

def get_current_year_month():
    """
    Returns the current year and month as a string in the format 'YYYYMM'.

    Returns:
        str: The current year and month in the format 'YYYYMM'.
    """
    return datetime.now().strftime('%Y%m')

class TestDateGeneration(unittest.TestCase):
    def test_february_leap_year(self):
        dates = generate_dates("202002")
        self.assertEqual(len(dates), 29)
        self.assertEqual(dates[0], "* 20200229 ")
        self.assertEqual(dates[-1], "* 20200201 ")

    def test_february_non_leap_year(self):
        dates = generate_dates("202103")
        self.assertEqual(len(dates), 31)
        self.assertEqual(dates[0], "* 20210331 ")
        self.assertEqual(dates[-1], "* 20210301 ")

    def test_single_digit_month(self):
        dates = generate_dates("202409")
        self.assertTrue(dates[0].startswith("* 202409"))
        self.assertEqual(len(dates), 30)

    def test_december(self):
        dates = generate_dates("202512")
        self.assertEqual(dates[0], "* 20251231 ")
        self.assertEqual(dates[-1], "* 20251201 ")
        self.assertEqual(len(dates), 31)

def main():
    parser = argparse.ArgumentParser(description="Generate reverse markdown dates or run tests.")
    parser.add_argument("--month", help="Generate dates for the given month in format YYYYMM")
    parser.add_argument("--tests", action="store_true", help="Run unit tests")
    args = parser.parse_args()

    if args.tests:
        unittest.main(argv=[sys.argv[0]], exit=False)
    elif args.month:
        result = generate_dates(args.month)
        for line in result:
            print(line)
    else:
        result = generate_dates(get_current_year_month())
        for line in result:
            print(line)

if __name__ == "__main__":
    main()
