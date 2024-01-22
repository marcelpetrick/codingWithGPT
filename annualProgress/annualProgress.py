import argparse
from datetime import datetime
import unittest

class YearProgressCalculator:
    """
    A class to calculate the progress of the current year.

    Attributes
    ----------
    None

    Methods
    -------
    is_leap_year(year)
        Determines if the specified year is a leap year.
    calculate_progress(date)
        Calculates the progress of the year for a given date.
    """

    @staticmethod
    def is_leap_year(year):
        """
        Determine if a given year is a leap year.

        A leap year is divisible by 4, except for end-of-century years, which must be divisible by 400.

        Parameters
        ----------
        year : int
            The year to check.

        Returns
        -------
        bool
            True if the year is a leap year, False otherwise.
        """
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

    def calculate_progress(self, date):
        """
        Calculate the progress of the year for a given date.

        The progress is calculated as the percentage of the year that has passed.

        Parameters
        ----------
        date : datetime
            The date for which to calculate the year's progress.

        Returns
        -------
        float
            The progress of the year as a percentage.
        """
        start_of_year = datetime(date.year, 1, 1)
        end_of_year = datetime(date.year + 1, 1, 1)
        total_days = (end_of_year - start_of_year).days
        days_passed = (date - start_of_year).days
        return (days_passed / total_days) * 100


class TestYearProgressCalculator(unittest.TestCase):
    """
    Unit tests for the YearProgressCalculator class.
    """

    def setUp(self):
        """
        Set up the test environment before each test.
        """
        self.calculator = YearProgressCalculator()

    def test_january_3rd(self):
        """
        Test the progress calculation for January 3rd.

        The test checks if the calculated progress for January 3rd is approximately 1%.
        """
        self.assertAlmostEqual(self.calculator.calculate_progress(datetime(2023, 1, 3)), 0.82, delta=0.05)
        self.assertAlmostEqual(self.calculator.calculate_progress(datetime(2024, 1, 3)), 0.81, delta=0.05)

    def test_february_29_leap_year(self):
        """
        Test the progress calculation for February 29th in a leap year.

        The test verifies the progress percentage for February 29th in a leap year.
        """
        self.assertAlmostEqual(self.calculator.calculate_progress(datetime(2024, 2, 29)), 16.12, delta=0.05)

    def test_february_28_non_leap_year(self):
        """
        Test the progress calculation for February 28th in a non-leap year.

        The test verifies the progress percentage for February 28th in a non-leap year.
        """
        self.assertAlmostEqual(self.calculator.calculate_progress(datetime(2023, 2, 28)), 15.62, delta=0.05)

def main():
    """
    Main function to handle command line arguments and execute the program.

    The program calculates the year's progress percentage based on the current date, a specified date,
    or runs unit tests depending on the arguments provided.
    """
    parser = argparse.ArgumentParser(description="Calculate the annual progress.")
    parser.add_argument('-tests', action='store_true', help='Run unit tests')
    parser.add_argument('-date', type=str, help='Calculate progress for a given date (format DD.MM.)')
    args = parser.parse_args()

    calculator = YearProgressCalculator()

    if args.tests:
        unittest.main(argv=['first-arg-is-ignored'], exit=False)
    elif args.date:
        date_str = args.date.strip('.')
        day, month = map(int, date_str.split('.'))
        specified_date = datetime(datetime.now().year, month, day)
        print(f"{calculator.calculate_progress(specified_date):.1f}%")
    else:
        print(f"{calculator.calculate_progress(datetime.now()):.1f}%")

if __name__ == "__main__":
    main()
