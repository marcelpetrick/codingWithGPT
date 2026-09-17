"""Reports over parsed entries."""


def monthly_totals(entries):
    """Sum amounts per calendar month.

    Returns a dict mapping "YYYY-MM" to the Decimal total, with its keys in
    chronological order. All entries must share one currency, otherwise
    ValueError is raised. An empty input returns an empty dict.
    """
    totals = {}
    for entry in entries:
        key = f"{entry.day.year}-{entry.day.month}"
        totals[key] = totals.get(key, 0) + entry.amount
    return totals


def category_breakdown(entries, month):
    """Totals per category for one month, given as "YYYY-MM".

    Returns a list of (category, total) tuples sorted by total ascending, so
    the largest expense comes first, with ties broken by category name.
    Categories whose total is exactly zero are left out. Entries from other
    months are ignored. Same single-currency rule as monthly_totals.
    """
    raise NotImplementedError
