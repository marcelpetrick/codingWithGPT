"""Parse ledger text into entries -- reference solution."""
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
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    fields = [f.strip() for f in line.split(";")]
    if len(fields) != 4:
        raise ValueError(f"expected 4 fields: {line!r}")
    day, category, amount, currency = fields
    currency = currency.upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError(f"bad currency: {currency!r}")
    return Entry(date.fromisoformat(day), category.lower(), parse_amount(amount), currency)


def parse_ledger(text):
    entries = (parse_line(line) for line in text.splitlines())
    return [entry for entry in entries if entry is not None]
