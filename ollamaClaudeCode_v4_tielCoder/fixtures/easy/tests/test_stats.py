import pytest

from stats import mean, median


def test_mean():
    assert mean([1, 2, 3, 4]) == 2.5


def test_median_odd():
    assert median([3, 1, 2]) == 2


def test_median_even():
    # With an even number of values the median is the mean of the two middle
    # values, not the upper one.
    assert median([1, 2, 3, 4]) == 2.5


def test_median_does_not_mutate():
    values = [3, 1, 2]
    median(values)
    assert values == [3, 1, 2]
