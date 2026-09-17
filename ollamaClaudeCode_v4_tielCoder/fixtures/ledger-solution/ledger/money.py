"""Money parsing -- reference solution, used only to validate the fixture."""
import re
from decimal import Decimal

_PATTERN = re.compile(r"[+-]?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?")


def parse_amount(text):
    s = text.strip()
    negative = False
    if s.startswith("(") and s.endswith(")"):
        s, negative = s[1:-1].strip(), True
    if not _PATTERN.fullmatch(s):
        raise ValueError(f"not an amount: {text!r}")
    value = Decimal(s.replace(",", "")).quantize(Decimal("0.01"))
    return -value if negative else value
