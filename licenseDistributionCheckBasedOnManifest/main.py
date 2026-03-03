#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""! @file license_manifest_summary.py
@brief Summarize license usage from a Yocto-like *.license.manifest file.

Parses component blocks like:
  PACKAGE NAME: foo
  PACKAGE VERSION: 1.2.3
  RECIPE NAME: foo
  LICENSE: MIT & GPL-2.0-or-later

For each component, the script resolves a single "chosen" license. If multiple
licenses are present, it prefers (in this order):
  1) MIT
  2) GPLv2 (GPL-2.0-*)
  3) LGPL v2/v2.1/v3 (LGPL-2.* or LGPL-3.*)

If none of the preferred licenses are found, it picks the first parsed license token.

Ambiguous/unparseable entries are reported.

Usage:
  ./license_manifest_summary.py path/to/file.manifest
  ./license_manifest_summary.py path/to/file.manifest --width 110
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from collections import Counter, defaultdict


# ----------------------------- Data Model -----------------------------


@dataclass(frozen=True)
class ComponentEntry:
    """! @brief One component entry parsed from the manifest.
    @param name PACKAGE NAME
    @param version PACKAGE VERSION (optional)
    @param recipe RECIPE NAME (optional)
    @param license_raw Raw LICENSE line content (optional/empty)
    """
    name: str
    version: str = ""
    recipe: str = ""
    license_raw: str = ""


@dataclass(frozen=True)
class Resolution:
    """! @brief Resolution result for a component.
    @param chosen Human-friendly chosen license label (or None if ambiguous)
    @param tokens Parsed SPDX-ish tokens (may be empty)
    @param reason If ambiguous, a short reason
    """
    chosen: Optional[str]
    tokens: Tuple[str, ...]
    reason: str = ""


# ----------------------------- Parsing -----------------------------


_RE_KEYVAL = re.compile(r"^\s*([A-Z][A-Z0-9 _-]*?)\s*:\s*(.*?)\s*$")
_RE_SPLIT_LICENSES = re.compile(
    r"\s*(?:&|\||,|\+|/|\bAND\b|\bOR\b)\s*", re.IGNORECASE
)


def parse_manifest(text: str) -> List[ComponentEntry]:
    """! @brief Parse manifest text into component entries.
    @param text Full manifest file content
    @return List of ComponentEntry
    """
    # Split on blank lines (blocks)
    blocks: List[List[str]] = []
    cur: List[str] = []
    for line in text.splitlines():
        if line.strip() == "":
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append(cur)

    entries: List[ComponentEntry] = []
    for b in blocks:
        fields: Dict[str, str] = {}
        for line in b:
            m = _RE_KEYVAL.match(line)
            if not m:
                # Ignore unrecognized lines; keep parser resilient
                continue
            k, v = m.group(1).strip(), m.group(2).strip()
            fields[k] = v

        name = fields.get("PACKAGE NAME", "").strip()
        if not name:
            # If a block doesn't have a package name, it's ambiguous; keep it but mark name
            name = "<UNKNOWN>"

        entries.append(
            ComponentEntry(
                name=name,
                version=fields.get("PACKAGE VERSION", "").strip(),
                recipe=fields.get("RECIPE NAME", "").strip(),
                license_raw=fields.get("LICENSE", "").strip(),
            )
        )

    return entries


# ----------------------------- License Resolution -----------------------------


def _normalize_spdx(token: str) -> str:
    """! @brief Normalize a license token for matching.
    @param token Raw token
    @return Normalized token
    """
    t = token.strip()
    # Remove surrounding parentheses and redundant whitespace
    t = t.strip("()[]{}").strip()
    return t


def _tokenize_license_expr(expr: str) -> Tuple[str, ...]:
    """! @brief Tokenize a license expression into candidate license IDs.
    @param expr Raw LICENSE field string
    @return Tuple of tokens (unique, in appearance order)
    """
    if not expr:
        return tuple()

    parts = [p for p in _RE_SPLIT_LICENSES.split(expr) if p and p.strip()]
    seen = set()
    out: List[str] = []
    for p in parts:
        t = _normalize_spdx(p)
        if not t:
            continue
        # Drop obviously non-license junk (very conservative)
        # Keep tokens with letters/digits and '-' '.' '+'
        if not re.search(r"[A-Za-z0-9]", t):
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
    return tuple(out)


def _friendly_label(token: str) -> str:
    """! @brief Map SPDX-ish IDs to friendly labels used in output.
    @param token SPDX-ish token
    @return Friendly label
    """
    t = token

    # MIT
    if t == "MIT":
        return "MIT"

    # GPL v2-ish
    if t.startswith("GPL-2.0"):
        return "GPLv2"

    # LGPL
    if t.startswith("LGPL-2.0"):
        return "LGPLv2"
    if t.startswith("LGPL-2.1"):
        return "LGPLv2.1"
    if t.startswith("LGPL-3.0"):
        return "LGPLv3"

    # Keep other SPDX identifiers as-is
    return t


def resolve_license(license_raw: str) -> Resolution:
    """! @brief Resolve a single chosen license for a component.
    @param license_raw Raw LICENSE field content
    @return Resolution with chosen license or ambiguous details
    """
    tokens = _tokenize_license_expr(license_raw)

    if not tokens:
        return Resolution(chosen=None, tokens=tuple(), reason="missing or empty LICENSE field")

    # Build sets for preference checks
    tok_set = set(tokens)

    # Preference order:
    # 1) MIT
    if "MIT" in tok_set:
        return Resolution(chosen="MIT", tokens=tokens)

    # 2) GPLv2: any GPL-2.0-*
    if any(t.startswith("GPL-2.0") for t in tokens):
        return Resolution(chosen="GPLv2", tokens=tokens)

    # 3) LGPL v2/v2.1/v3
    if any(t.startswith("LGPL-2.0") for t in tokens):
        return Resolution(chosen="LGPLv2", tokens=tokens)
    if any(t.startswith("LGPL-2.1") for t in tokens):
        return Resolution(chosen="LGPLv2.1", tokens=tokens)
    if any(t.startswith("LGPL-3.0") for t in tokens):
        return Resolution(chosen="LGPLv3", tokens=tokens)

    # If there's only one license token, take it (friendly label)
    if len(tokens) == 1:
        return Resolution(chosen=_friendly_label(tokens[0]), tokens=tokens)

    # Otherwise pick first token, but mark that it was a fallback
    chosen = _friendly_label(tokens[0])
    return Resolution(
        chosen=chosen,
        tokens=tokens,
        reason="multiple licenses; no preferred match, picked first token as fallback",
    )


# ----------------------------- Output Rendering -----------------------------


def _term_width(explicit: Optional[int] = None) -> int:
    """! @brief Determine terminal width with fallback.
    @param explicit User-provided width
    @return Width in columns
    """
    if explicit and explicit > 40:
        return explicit
    try:
        return shutil.get_terminal_size((100, 20)).columns
    except Exception:
        return 100


def _bar(count: int, max_count: int, width: int) -> str:
    """! @brief Create an ASCII bar for a given count scaled to width.
    @param count Current count
    @param max_count Maximum count in dataset
    @param width Maximum bar width
    @return Bar string
    """
    if max_count <= 0 or width <= 0:
        return ""
    # Use a mix for nicer look; keep it terminal-safe
    # scale length at least 1 for non-zero counts if width allows
    n = int(round((count / max_count) * width))
    if count > 0 and n == 0 and width > 0:
        n = 1
    return "█" * n


def print_summary(
    chosen_counts: Counter[str],
    total_components: int,
    resolved_components: int,
    ambiguous: List[Tuple[ComponentEntry, Resolution]],
    width: int,
    show_ambiguous: int,
) -> None:
    """! @brief Print a terminal-friendly summary report.
    @param chosen_counts Counter of chosen license -> component count
    @param total_components Total unique components
    @param resolved_components Number resolved to a license
    @param ambiguous List of ambiguous entries
    @param width Terminal width
    @param show_ambiguous Number of ambiguous lines to show (0 = all)
    """
    title = "📦 License Summary"
    print(title)
    print("─" * min(width, max(60, len(title) + 10)))

    ambiguous_n = len(ambiguous)
    print(f"Components: {total_components}   ✅ resolved: {resolved_components}   ⚠️ ambiguous: {ambiguous_n}")
    print()

    if not chosen_counts:
        print("⚠️ No resolvable licenses found.")
        return

    # Layout calculation
    max_license_len = max(len(k) for k in chosen_counts.keys())
    max_count = max(chosen_counts.values())

    # Reserve space: "LICENSE  12345  | " + bar
    count_width = max(5, len(str(max_count)))
    prefix_width = max_license_len + 2 + count_width + 3  # "  |"
    bar_width = max(10, width - prefix_width - 1)

    # Sort: highest count first, then name
    items = sorted(chosen_counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))

    print("📊 By chosen license (components):")
    for lic, cnt in items:
        b = _bar(cnt, max_count, bar_width)
        print(f"{lic:<{max_license_len}}  {cnt:>{count_width}}  | {b}")
    print()

    # Optional: show percentages
    print("🧮 Percent of resolved components:")
    for lic, cnt in items:
        pct = (cnt / resolved_components * 100.0) if resolved_components else 0.0
        print(f"  - {lic}: {pct:5.1f}%")
    print()

    if ambiguous_n:
        print("⚠️ Ambiguous / problematic entries:")
        to_show = ambiguous if show_ambiguous == 0 else ambiguous[:show_ambiguous]
        for entry, res in to_show:
            name = entry.name
            raw = entry.license_raw if entry.license_raw else "<empty>"
            why = res.reason if res.reason else "could not resolve"
            tokens = ", ".join(res.tokens) if res.tokens else "<none>"
            print(f"  - {name}: {why}")
            print(f"    LICENSE: {raw}")
            print(f"    tokens:  {tokens}")
        if show_ambiguous != 0 and ambiguous_n > show_ambiguous:
            print(f"  … and {ambiguous_n - show_ambiguous} more (use --show-ambiguous 0 to show all)")
        print()


# ----------------------------- Main -----------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    """! @brief Program entry point.
    @param argv Optional argv override (for testing)
    @return Process exit code
    """
    parser = argparse.ArgumentParser(
        description="Summarize license usage from a *.license.manifest file."
    )
    parser.add_argument(
        "manifest",
        help="Path to the manifest file (e.g. *.license.manifest).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Override terminal width (columns).",
    )
    parser.add_argument(
        "--show-ambiguous",
        type=int,
        default=25,
        help="How many ambiguous entries to print (0 = all). Default: 25.",
    )

    args = parser.parse_args(argv)

    if not os.path.isfile(args.manifest):
        print(f"❌ File not found: {args.manifest}", file=sys.stderr)
        return 2

    try:
        with open(args.manifest, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception as e:
        print(f"❌ Failed to read file: {e}", file=sys.stderr)
        return 2

    entries = parse_manifest(text)

    # Treat PACKAGE NAME as "component". If a component repeats (common), merge:
    # - Prefer first non-empty version/recipe/license_raw encountered for reporting.
    by_component: Dict[str, ComponentEntry] = {}
    licenses_seen: Dict[str, List[str]] = defaultdict(list)

    for e in entries:
        if e.name not in by_component:
            by_component[e.name] = e
        # Keep all raw license strings (some manifests may have multiple package rows per component)
        if e.license_raw:
            licenses_seen[e.name].append(e.license_raw)

    # Resolve per component. If multiple raw licenses differ, join with " | " for tokenization,
    # and flag it as potentially ambiguous (but still resolvable).
    chosen_counts: Counter[str] = Counter()
    ambiguous: List[Tuple[ComponentEntry, Resolution]] = []
    resolved = 0

    for name, base_entry in sorted(by_component.items(), key=lambda kv: kv[0].lower()):
        raws = licenses_seen.get(name, [])
        if not raws:
            merged_raw = base_entry.license_raw  # might be empty
        else:
            # Deduplicate while preserving order
            seen = set()
            uniq = []
            for r in raws:
                if r not in seen:
                    uniq.append(r)
                    seen.add(r)
            merged_raw = " | ".join(uniq)

        res = resolve_license(merged_raw)

        if res.chosen is None:
            ambiguous.append((base_entry, res))
            continue

        chosen_counts[res.chosen] += 1
        resolved += 1

        # If we used fallback-with-reason, still count it but report as "ambiguous-ish"
        if res.reason:
            # Only flag stronger ambiguity if there were multiple distinct raw license strings
            if len(set(raws)) > 1:
                ambiguous.append((base_entry, Resolution(
                    chosen=res.chosen, tokens=res.tokens,
                    reason=f"{res.reason}; also multiple differing LICENSE lines for this component"
                )))

    width = _term_width(args.width)
    print_summary(
        chosen_counts=chosen_counts,
        total_components=len(by_component),
        resolved_components=resolved,
        ambiguous=ambiguous,
        width=width,
        show_ambiguous=args.show_ambiguous,
    )

    # Exit non-zero if ambiguous (so CI can catch it), but still print the summary.
    return 1 if ambiguous else 0


if __name__ == "__main__":
    raise SystemExit(main())
