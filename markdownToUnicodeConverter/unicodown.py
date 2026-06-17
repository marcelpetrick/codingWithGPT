#!/usr/bin/env python3
"""Unicodown — convert inline Markdown styling to Unicode styled characters."""

import argparse
import re
import sys

# ---------------------------------------------------------------------------
# Translation tables (Mathematical Alphanumeric Symbols block, U+1D400+)
# ---------------------------------------------------------------------------

_BOLD_UPPER = (
    "\U0001D5D4\U0001D5D5\U0001D5D6\U0001D5D7\U0001D5D8\U0001D5D9"
    "\U0001D5DA\U0001D5DB\U0001D5DC\U0001D5DD\U0001D5DE\U0001D5DF"
    "\U0001D5E0\U0001D5E1\U0001D5E2\U0001D5E3\U0001D5E4\U0001D5E5"
    "\U0001D5E6\U0001D5E7\U0001D5E8\U0001D5E9\U0001D5EA\U0001D5EB"
    "\U0001D5EC\U0001D5ED"
)
_BOLD_LOWER = (
    "\U0001D5EE\U0001D5EF\U0001D5F0\U0001D5F1\U0001D5F2\U0001D5F3"
    "\U0001D5F4\U0001D5F5\U0001D5F6\U0001D5F7\U0001D5F8\U0001D5F9"
    "\U0001D5FA\U0001D5FB\U0001D5FC\U0001D5FD\U0001D5FE\U0001D5FF"
    "\U0001D600\U0001D601\U0001D602\U0001D603\U0001D604\U0001D605"
    "\U0001D606\U0001D607"
)
_BOLD_DIGITS = (
    "\U0001D7EC\U0001D7ED\U0001D7EE\U0001D7EF\U0001D7F0"
    "\U0001D7F1\U0001D7F2\U0001D7F3\U0001D7F4\U0001D7F5"
)

BOLD: dict[int, int] = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    _BOLD_UPPER + _BOLD_LOWER + _BOLD_DIGITS,
)

_ITALIC_UPPER = (
    "\U0001D608\U0001D609\U0001D60A\U0001D60B\U0001D60C\U0001D60D"
    "\U0001D60E\U0001D60F\U0001D610\U0001D611\U0001D612\U0001D613"
    "\U0001D614\U0001D615\U0001D616\U0001D617\U0001D618\U0001D619"
    "\U0001D61A\U0001D61B\U0001D61C\U0001D61D\U0001D61E\U0001D61F"
    "\U0001D620\U0001D621"
)
_ITALIC_LOWER = (
    "\U0001D622\U0001D623\U0001D624\U0001D625\U0001D626\U0001D627"
    "\U0001D628\U0001D629\U0001D62A\U0001D62B\U0001D62C\U0001D62D"
    "\U0001D62E\U0001D62F\U0001D630\U0001D631\U0001D632\U0001D633"
    "\U0001D634\U0001D635\U0001D636\U0001D637\U0001D638\U0001D639"
    "\U0001D63A\U0001D63B"
)

ITALIC: dict[int, int] = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    _ITALIC_UPPER + _ITALIC_LOWER,
)

_MONO_UPPER = (
    "\U0001D670\U0001D671\U0001D672\U0001D673\U0001D674\U0001D675"
    "\U0001D676\U0001D677\U0001D678\U0001D679\U0001D67A\U0001D67B"
    "\U0001D67C\U0001D67D\U0001D67E\U0001D67F\U0001D680\U0001D681"
    "\U0001D682\U0001D683\U0001D684\U0001D685\U0001D686\U0001D687"
    "\U0001D688\U0001D689"
)
_MONO_LOWER = (
    "\U0001D68A\U0001D68B\U0001D68C\U0001D68D\U0001D68E\U0001D68F"
    "\U0001D690\U0001D691\U0001D692\U0001D693\U0001D694\U0001D695"
    "\U0001D696\U0001D697\U0001D698\U0001D699\U0001D69A\U0001D69B"
    "\U0001D69C\U0001D69D\U0001D69E\U0001D69F\U0001D6A0\U0001D6A1"
    "\U0001D6A2\U0001D6A3"
)
_MONO_DIGITS = (
    "\U0001D7F6\U0001D7F7\U0001D7F8\U0001D7F9\U0001D7FA"
    "\U0001D7FB\U0001D7FC\U0001D7FD\U0001D7FE\U0001D7FF"
)

MONO: dict[int, int] = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    _MONO_UPPER + _MONO_LOWER + _MONO_DIGITS,
)

# U+0336 COMBINING LONG STROKE OVERLAY — inserted after every character
_STRIKE_CHAR = "̶"


def _strike(text: str) -> str:
    return "".join(ch + _STRIKE_CHAR for ch in text)


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------

def convert(text: str) -> str:
    """Return *text* with inline Markdown styling replaced by Unicode chars."""
    # Order matters: backtick mono first so its content is protected from
    # further substitution passes (translated chars won't match later patterns).
    text = re.sub(r"`([^`\n]+)`", lambda m: m.group(1).translate(MONO), text)
    text = re.sub(
        r"\*\*([^*\n]+)\*\*", lambda m: m.group(1).translate(BOLD), text
    )
    text = re.sub(
        r"__([^\W_][^_\n]*)__", lambda m: m.group(1).translate(BOLD), text
    )
    text = re.sub(r"\*([^*\n]+)\*", lambda m: m.group(1).translate(ITALIC), text)
    text = re.sub(
        r"_([^\W_][^_\n]*)_", lambda m: m.group(1).translate(ITALIC), text
    )
    text = re.sub(r"~~([^~\n]+)~~", lambda m: _strike(m.group(1)), text)
    return text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="unicodown",
        description=(
            "Convert inline Markdown styling (**bold**, *italic*, `mono`, "
            "~~strike~~) to Unicode-styled characters."
        ),
    )
    parser.add_argument(
        "input",
        nargs="?",
        metavar="FILE",
        help="Input file (default: stdin).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Output file (default: stdout).",
    )
    args = parser.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()

    result = convert(text)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(result)
    else:
        sys.stdout.write(result)


if __name__ == "__main__":
    main()
