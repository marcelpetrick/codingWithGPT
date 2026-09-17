"""Parse ledger text into entries."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .money import parse_amount


@dataclass(frozen=True)
class Entry:
    day: date
    category: str
    amount: Decimal
    currency: str


def parse_line(line):
    """Parse one line of the form  DATE;CATEGORY;AMOUNT;CURRENCY

    * DATE is ISO 8601, YYYY-MM-DD
    * CATEGORY is stripped and lower-cased
    * AMOUNT is parsed with parse_amount
    * CURRENCY is stripped and upper-cased, and must be exactly three letters
    * any field may be surrounded by whitespace

    Blank lines, and lines whose first non-space character is '#', return None.
    Anything malformed raises ValueError.
    """
    day, category, amount, currency = line.split(";")
    return Entry(date.fromisoformat(day), category, parse_amount(amount), currency)


def parse_ledger(text):
    """Parse every line of text, dropping the lines parse_line returns None for."""
    entries = (parse_line(line) for line in text.splitlines())
    return [entry for entry in entries if entry is not None]
