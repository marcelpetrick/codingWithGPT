"""Reports over parsed entries -- reference solution."""
from decimal import Decimal


def _one_currency(entries):
    if len({e.currency for e in entries}) > 1:
        raise ValueError("mixed currencies")


def monthly_totals(entries):
    _one_currency(entries)
    totals = {}
    for entry in sorted(entries, key=lambda e: e.day):
        key = f"{entry.day.year:04d}-{entry.day.month:02d}"
        totals[key] = totals.get(key, Decimal("0.00")) + entry.amount
    return totals


def category_breakdown(entries, month):
    _one_currency(entries)
    totals = {}
    for entry in entries:
        if f"{entry.day.year:04d}-{entry.day.month:02d}" == month:
            totals[entry.category] = totals.get(entry.category, Decimal("0.00")) + entry.amount
    return sorted(((c, t) for c, t in totals.items() if t != 0), key=lambda ct: (ct[1], ct[0]))
