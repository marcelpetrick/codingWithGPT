import unittest
from annual_progress import is_leap_year, annual_progress_percentage


class TestYearProgress(unittest.TestCase):

    def test_is_leap_year(self):
        self.assertTrue(is_leap_year(2020))
        self.assertTrue(is_leap_year(2000))
        self.assertFalse(is_leap_year(1900))
        self.assertFalse(is_leap_year(2021))
        self.assertFalse(is_leap_year(2023))

    def test_percentage_non_leap(self):
        # 1 Jan
        self.assertEqual(annual_progress_percentage(1, 2023), 0)
        # Middle of year (183rd day of 365)
        self.assertEqual(annual_progress_percentage(183, 2023), 50)
        # End of year
        self.assertEqual(annual_progress_percentage(365, 2023), 100)

    def test_percentage_leap(self):
        # 1 Jan
        self.assertEqual(annual_progress_percentage(1, 2020), 0)
        # Middle of year (183rd day of 366)
        self.assertEqual(annual_progress_percentage(183, 2020), 50)
        # End of year
        self.assertEqual(annual_progress_percentage(366, 2020), 100)


if __name__ == '__main__':
    unittest.main()
