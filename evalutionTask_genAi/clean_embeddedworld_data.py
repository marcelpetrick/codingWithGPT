#!/usr/bin/env python3
"""Clean embedded world exhibitor markdown into a homogeneous table."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_INPUT = Path("Embeddedworld_exhibitors_sw_germany_2026.md")
DEFAULT_OUTPUT = Path("cleaned_data.md")

COUNTRIES = {"Germany"}
NOISE_LINES = {
    "Default company logo",
    "embedded world 2026 - xhibitors for softwaree, germany.",
    "------",
}
ORGANIZATION_TYPES = {
    "Association / Authority / Other organisation",
    "Consulting",
    "Distributor",
    "Manufacturer",
    "Other",
    "Research & Development",
    "Reseller / Wholesale",
    "Service",
    "Start-up",
    "Supplier",
}
HALL_RE = re.compile(r"^Hall\s+(.+?)\s*/\s*(.+)$")


@dataclass
class Vendor:
    name: str
    halls: list[str] = field(default_factory=list)
    organization_types: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def markdown_escape(value: str) -> str:
    return value.replace("|", r"\|")


def clean_lines(raw_text: str) -> list[str]:
    cleaned: list[str] = []
    for raw_line in raw_text.splitlines():
        line = normalize_whitespace(raw_line)
        if not line or line in NOISE_LINES:
            continue
        cleaned.append(line)
    return cleaned


def parse_vendors(raw_text: str) -> list[Vendor]:
    vendors: list[Vendor] = []
    current: Vendor | None = None
    pending_names: list[str] = []

    def start_vendor_from_pending() -> Vendor | None:
        nonlocal pending_names
        names = dedupe_preserve_order(pending_names)
        pending_names = []
        if not names:
            return None
        return Vendor(name=names[0])

    def finish_current() -> None:
        nonlocal current
        if current is not None:
            current.halls = dedupe_preserve_order(current.halls)
            current.organization_types = dedupe_preserve_order(current.organization_types)
            current.countries = dedupe_preserve_order(current.countries)
            vendors.append(current)
            current = None

    for line in clean_lines(raw_text):
        if HALL_RE.match(line):
            if current is None:
                current = start_vendor_from_pending()
            if current is not None:
                current.halls.append(line)
            continue

        if line in ORGANIZATION_TYPES:
            if current is None:
                current = start_vendor_from_pending()
            if current is not None:
                current.organization_types.append(line)
            continue

        if line in COUNTRIES:
            if current is None:
                current = start_vendor_from_pending()
            if current is not None:
                current.countries.append(line)
                finish_current()
            continue

        if current is not None:
            finish_current()
        pending_names.append(line)

    if current is None:
        current = start_vendor_from_pending()
    finish_current()

    return merge_duplicate_vendors(vendors)


def merge_duplicate_vendors(vendors: list[Vendor]) -> list[Vendor]:
    merged: dict[str, Vendor] = {}
    original_order: dict[str, int] = {}

    for index, vendor in enumerate(vendors):
        key = vendor.name.casefold()
        original_order.setdefault(key, index)
        if key not in merged:
            merged[key] = Vendor(name=vendor.name)
        merged_vendor = merged[key]
        merged_vendor.halls.extend(vendor.halls)
        merged_vendor.organization_types.extend(vendor.organization_types)
        merged_vendor.countries.extend(vendor.countries)

    result = []
    for key, vendor in merged.items():
        vendor.halls = dedupe_preserve_order(vendor.halls)
        vendor.organization_types = dedupe_preserve_order(vendor.organization_types)
        vendor.countries = dedupe_preserve_order(vendor.countries)
        result.append(vendor)

    return sorted(result, key=lambda vendor: vendor.name.casefold())


def render_markdown(vendors: list[Vendor], source_name: str) -> str:
    type_counter = Counter(
        organization_type or "Unspecified"
        for vendor in vendors
        for organization_type in (vendor.organization_types or ["Unspecified"])
    )
    country_counter = Counter(
        country or "Unspecified"
        for vendor in vendors
        for country in (vendor.countries or ["Unspecified"])
    )

    lines = [
        "# Cleaned Embedded World 2026 Software Exhibitors - Germany",
        "",
        f"Source: `{source_name}`",
        "",
        "## Summary",
        "",
        f"- Vendors: {len(vendors)}",
        f"- Countries: {', '.join(f'{name} ({count})' for name, count in sorted(country_counter.items()))}",
        f"- Organization types: {', '.join(f'{name} ({count})' for name, count in sorted(type_counter.items()))}",
        "",
        "## Vendors",
        "",
        "| Vendor | Hall / Booth | Organization Type | Country |",
        "| --- | --- | --- | --- |",
    ]

    for vendor in vendors:
        halls = ", ".join(vendor.halls) if vendor.halls else "Unspecified"
        organization_types = ", ".join(vendor.organization_types) if vendor.organization_types else "Unspecified"
        countries = ", ".join(vendor.countries) if vendor.countries else "Unspecified"
        lines.append(
            "| "
            + " | ".join(
                markdown_escape(value)
                for value in [vendor.name, halls, organization_types, countries]
            )
            + " |"
        )

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean embedded world exhibitor data into homogeneous markdown."
    )
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    raw_text = args.input.read_text(encoding="utf-8")
    vendors = parse_vendors(raw_text)
    args.output.write_text(render_markdown(vendors, args.input.name), encoding="utf-8")
    print(f"Wrote {len(vendors)} vendors to {args.output}")


if __name__ == "__main__":
    main()
