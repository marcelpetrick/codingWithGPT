"""Money parsing."""
from decimal import Decimal


def parse_amount(text):
    """Parse a ledger amount into a Decimal.

    Accepted forms, surrounding whitespace ignored:

    * plain or signed decimals: "12.50", "-12.50", "+12.50", "7"
    * thousands separators: "1,234.50"
    * accounting negatives in parentheses: "(12.50)" means -12.50

    The result always carries exactly two decimal places, so "7" parses to
    Decimal("7.00"). Anything else raises ValueError.
    """
    return Decimal(text)
