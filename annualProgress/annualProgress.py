# annualProgress.py

from datetime import datetime, timedelta

def is_leap_year(year):
    """ Check if a year is a leap year """
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def year_progress(today):
    """ Calculate the percentage of the year that has passed """
    start_of_year = datetime(today.year, 1, 1)
    end_of_year = datetime(today.year + 1, 1, 1)
    total_days = (end_of_year - start_of_year).days
    days_passed = (today - start_of_year).days

    return (days_passed / total_days) * 100


import unittest

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

# Run the unit tests
unittest.main(argv=[''], exit=False)
