from datetime import date
from decimal import Decimal

import pytest

from ledger.money import parse_amount
from ledger.parser import Entry, parse_ledger, parse_line
from ledger.report import category_breakdown, monthly_totals

SAMPLE = """\
# September, first week
2026-09-01; Groceries ;-45.20; eur
2026-09-02;Rent;(1,200.00);EUR

2026-08-30;salary;3,000;EUR
2026-09-03;groceries;-15.50;EUR
"""


def test_parse_amount_thousands_separator():
    assert parse_amount("1,234.50") == Decimal("1234.50")


def test_parse_amount_parentheses_are_negative():
    assert parse_amount("(12.50)") == Decimal("-12.50")


def test_parse_amount_always_two_places():
    assert str(parse_amount("7")) == "7.00"


def test_parse_amount_rejects_garbage():
    with pytest.raises(ValueError):
        parse_amount("twelve")


def test_parse_line_normalises_fields():
    assert parse_line("2026-09-01; Groceries ;-45.20; eur") == Entry(
        date(2026, 9, 1), "groceries", Decimal("-45.20"), "EUR"
    )


def test_parse_line_skips_comments_and_blanks():
    assert parse_line("# a comment") is None
    assert parse_line("   ") is None


def test_parse_ledger_sample():
    assert len(parse_ledger(SAMPLE)) == 4


def test_monthly_totals_are_chronological_and_zero_padded():
    totals = monthly_totals(parse_ledger(SAMPLE))
    assert list(totals) == ["2026-08", "2026-09"]
    assert totals["2026-09"] == Decimal("-1260.70")


def test_category_breakdown_largest_expense_first():
    assert category_breakdown(parse_ledger(SAMPLE), "2026-09") == [
        ("rent", Decimal("-1200.00")),
        ("groceries", Decimal("-60.70")),
    ]
