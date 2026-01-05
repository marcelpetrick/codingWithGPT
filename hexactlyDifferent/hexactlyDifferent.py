#!/usr/bin/env python3
"""
ILITEK Intel HEX: unify BOTH inputs, dump BOTH, then diff the unified layouts.

Behavior:
  1) Read exactly two Intel HEX file paths (A and B).
  2) Parse both (types 00/01/02/04), strict checksum validation.
  3) Discover unified bounds [lowest, highest] across BOTH.
  4) Enforce max unified size (default 1 MiB).
  5) Build unified layouts for BOTH using the same fill byte.
  6) Dump BOTH to:
       <file_a_basename>.unified.txt
       <file_b_basename>.unified.txt
     - If output exists, remove first.
     - Header is mandatory, exactly 4 lines; content begins at line 5.
  7) Diff the unified layouts (address-based, NOT text diff):
     - If identical: print "IDENTICAL" to stdout and exit 0.
     - If different: print all differing lines (hex-editor style) to stdout and exit 1.

Diff output format (per differing line):
  0xAAAAAAAA: <A hex bytes>  |<A ASCII>|   <B hex bytes>  |<B ASCII>|   <diff markers>
Where diff markers is a string of length N (block width), with '^' where bytes differ, '.' otherwise.

Block width:
  - default 16, supports 8 or 16.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


EXIT_OK = 0
EXIT_DIFF_FOUND = 1
EXIT_USAGE_ERROR = 2
EXIT_PARSE_OR_RANGE_ERROR = 3


@dataclass(frozen=True)
class WriteOrigin:
    file_path: str
    line_no: int


class IntelHexParseError(RuntimeError):
    def __init__(self, message: str, file_path: str, line_no: int):
        super().__init__(f"{file_path}:{line_no}: {message}")
        self.file_path = file_path
        self.line_no = line_no


def _hex_to_int(h: str, file_path: str, line_no: int) -> int:
    try:
        return int(h, 16)
    except ValueError:
        raise IntelHexParseError(f"Invalid hex value: {h!r}", file_path, line_no)


def _parse_record(line: str, file_path: str, line_no: int) -> Tuple[int, int, int, bytes, int]:
    """
    Returns: (byte_count, address16, record_type, data_bytes, checksum)
    """
    s = line.strip()  # tolerate extraneous whitespace in input lines
    if not s:
        raise IntelHexParseError("Empty line is not a valid Intel HEX record.", file_path, line_no)
    if not s.startswith(":"):
        raise IntelHexParseError("Record does not start with ':'.", file_path, line_no)

    payload = s[1:]
    if len(payload) < 10:
        raise IntelHexParseError("Record too short.", file_path, line_no)
    if len(payload) % 2 != 0:
        raise IntelHexParseError("Record has odd number of hex characters.", file_path, line_no)

    byte_count = _hex_to_int(payload[0:2], file_path, line_no)
    address16 = _hex_to_int(payload[2:6], file_path, line_no)
    record_type = _hex_to_int(payload[6:8], file_path, line_no)

    data_hex = payload[8:-2]
    checksum = _hex_to_int(payload[-2:], file_path, line_no)

    expected_data_chars = byte_count * 2
    if len(data_hex) != expected_data_chars:
        raise IntelHexParseError(
            f"Byte count {byte_count} does not match data length ({len(data_hex)//2} bytes).",
            file_path,
            line_no,
        )

    try:
        data = bytes.fromhex(data_hex) if data_hex else b""
    except ValueError:
        raise IntelHexParseError("Data field contains non-hex characters.", file_path, line_no)

    # Checksum: sum(all bytes including checksum) % 256 == 0
    total = byte_count + ((address16 >> 8) & 0xFF) + (address16 & 0xFF) + record_type + sum(data) + checksum
    if (total & 0xFF) != 0:
        raise IntelHexParseError(
            f"Checksum mismatch (computed sum mod 256 = {total & 0xFF:02X}, expected 00).",
            file_path,
            line_no,
        )

    return byte_count, address16, record_type, data, checksum


def parse_intel_hex(
    file_path: str,
    *,
    verbose: int = 0,
) -> Tuple[Dict[int, int], Optional[int], Optional[int], int, int]:
    """
    Parse Intel HEX file into:
      - memory_map: absolute_address -> byte_value (0..255)
      - min_addr, max_addr over all data bytes (None if no data)
      - records_processed, bytes_mapped

    Supported record types: 00, 01, 02, 04.
    Overlaps: last write wins; warning with -v.
    """
    memory: Dict[int, int] = {}
    origins: Dict[int, WriteOrigin] = {}

    base = 0
    min_addr: Optional[int] = None
    max_addr: Optional[int] = None
    records = 0
    mapped = 0

    try:
        with open(file_path, "r", encoding="ascii", errors="strict") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.rstrip("\n")
                if not line.strip():
                    # tolerate blank lines
                    continue

                byte_count, addr16, rectype, data, _ck = _parse_record(line, file_path, line_no)
                records += 1

                if rectype == 0x00:  # Data
                    abs_start = base + addr16
                    for i, b in enumerate(data):
                        a = abs_start + i
                        if a in memory and verbose >= 1:
                            prev = origins.get(a)
                            prev_txt = f"{prev.file_path}:{prev.line_no}" if prev else "unknown"
                            print(
                                f"WARN: overlap at 0x{a:08X}: {prev_txt} overwritten by {file_path}:{line_no}",
                                file=sys.stderr,
                            )
                        memory[a] = b
                        origins[a] = WriteOrigin(file_path=file_path, line_no=line_no)
                        mapped += 1

                        if min_addr is None or a < min_addr:
                            min_addr = a
                        if max_addr is None or a > max_addr:
                            max_addr = a

                elif rectype == 0x01:  # EOF
                    break

                elif rectype == 0x04:  # Extended Linear Address
                    if byte_count != 2:
                        raise IntelHexParseError("Type 04 record must have byte count 2.", file_path, line_no)
                    upper = (data[0] << 8) | data[1]
                    base = upper << 16

                elif rectype == 0x02:  # Extended Segment Address
                    if byte_count != 2:
                        raise IntelHexParseError("Type 02 record must have byte count 2.", file_path, line_no)
                    seg = (data[0] << 8) | data[1]
                    base = seg << 4

                else:
                    if verbose >= 2:
                        print(
                            f"INFO: Ignoring unsupported record type 0x{rectype:02X} at {file_path}:{line_no}",
                            file=sys.stderr,
                        )

    except FileNotFoundError:
        raise IntelHexParseError("File not found.", file_path, 0)
    except UnicodeDecodeError:
        raise IntelHexParseError("File is not valid ASCII text.", file_path, 0)

    return memory, min_addr, max_addr, records, mapped


def compute_unified_bounds(
    a_min: Optional[int], a_max: Optional[int],
    b_min: Optional[int], b_max: Optional[int],
) -> Tuple[int, int]:
    mins = [x for x in (a_min, b_min) if x is not None]
    maxs = [x for x in (a_max, b_max) if x is not None]
    if not mins or not maxs:
        raise ValueError("No data bytes found in either input.")
    return min(mins), max(maxs)


def build_unified_layout(
    memory_map: Dict[int, int],
    lowest: int,
    highest: int,
    *,
    fill_byte: int,
) -> bytearray:
    size = (highest - lowest) + 1
    buf = bytearray([fill_byte] * size)
    for addr, val in memory_map.items():
        if lowest <= addr <= highest:
            buf[addr - lowest] = val
    return buf


def derive_output_path(src_file: str) -> str:
    base, ext = os.path.splitext(src_file)
    if ext.lower() == ".hex":
        return base + ".unified.txt"
    return src_file + ".unified.txt"


def mandatory_header_lines(source_path: str, lowest: int, highest: int, size: int) -> List[str]:
    # Exactly 4 lines; content begins at line 5
    return [
        "# UNIFIED_MEMORY_LAYOUT v1",
        f"# SOURCE {source_path}",
        f"# RANGE 0x{lowest:08X} 0x{highest:08X} SIZE {size}",
        "# FORMAT: 0xAAAAAAAA: <hex bytes>  |<ASCII>|   (CONTENT_STARTS_AT_LINE 5)",
    ]


def dump_unified_layout(
    out_path: str,
    layout: bytearray,
    *,
    source_path: str,
    lowest: int,
    highest: int,
    width: int,
) -> None:
    def to_ascii(b: int) -> str:
        return chr(b) if 0x20 <= b <= 0x7E else "."

    # Remove existing output first
    try:
        if os.path.exists(out_path):
            os.remove(out_path)
    except OSError as e:
        raise RuntimeError(f"Failed to remove existing output file {out_path!r}: {e}") from e

    size = len(layout)
    header = mandatory_header_lines(source_path, lowest, highest, size)

    with open(out_path, "w", encoding="utf-8", newline="\n") as w:
        for line in header:
            w.write(line + "\n")

        # Content starts at line 5: no blank line inserted
        for offset in range(0, size, width):
            addr = lowest + offset
            chunk = layout[offset : offset + width]
            hex_bytes = " ".join(f"{b:02X}" for b in chunk)
            if len(chunk) < width:
                hex_bytes += "   " * (width - len(chunk))
            ascii_col = "".join(to_ascii(b) for b in chunk)
            w.write(f"0x{addr:08X}: {hex_bytes}  |{ascii_col}|\n")


def _ascii_of_chunk(chunk: bytes) -> str:
    return "".join(chr(b) if 0x20 <= b <= 0x7E else "." for b in chunk)


def _hex_bytes(chunk: bytes, width: int) -> str:
    s = " ".join(f"{b:02X}" for b in chunk)
    if len(chunk) < width:
        s += "   " * (width - len(chunk))
    return s


def diff_and_print(
    layout_a: bytearray,
    layout_b: bytearray,
    *,
    lowest: int,
    width: int,
) -> Tuple[int, int]:
    """
    Prints differing lines only.

    Returns: (diff_bytes_total, diff_lines_total)
    """
    if len(layout_a) != len(layout_b):
        # Should not happen, but keep deterministic failure mode
        raise RuntimeError("Internal error: unified layouts have different lengths.")

    size = len(layout_a)
    diff_bytes_total = 0
    diff_lines_total = 0

    for offset in range(0, size, width):
        a_chunk = bytes(layout_a[offset : offset + width])
        b_chunk = bytes(layout_b[offset : offset + width])

        # Fast check: if identical block, skip
        if a_chunk == b_chunk:
            continue

        # Determine per-byte differences for this block
        markers = []
        for i in range(len(a_chunk)):
            if a_chunk[i] != b_chunk[i]:
                markers.append("^")
                diff_bytes_total += 1
            else:
                markers.append(".")

        diff_lines_total += 1
        addr = lowest + offset

        a_hex = _hex_bytes(a_chunk, width)
        b_hex = _hex_bytes(b_chunk, width)
        a_ascii = _ascii_of_chunk(a_chunk)
        b_ascii = _ascii_of_chunk(b_chunk)

        # markers length should be width; pad if last line shorter
        if len(a_chunk) < width:
            markers.extend(" " * (width - len(a_chunk)))

        marker_str = "".join(markers)

        print(
            f"0x{addr:08X}: "
            f"{a_hex}  |{a_ascii}|   "
            f"{b_hex}  |{b_ascii}|   "
            f"{marker_str}"
        )

    return diff_bytes_total, diff_lines_total


def parse_hex_byte(s: str) -> int:
    s = s.strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    if len(s) != 2:
        raise ValueError("Fill byte must be exactly one byte (e.g., FF or 0xFF).")
    v = int(s, 16)
    if not (0 <= v <= 0xFF):
        raise ValueError("Fill byte out of range.")
    return v


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="hexactlyDifferent.py",
        description="Unify BOTH Intel HEX inputs into address-based layouts, dump BOTH, then diff them.",
    )
    ap.add_argument("file_a", help="Path to file A (Intel HEX).")
    ap.add_argument("file_b", help="Path to file B (Intel HEX).")
    ap.add_argument("--max-size", type=int, default=1048576, help="Maximum unified range size in bytes (default: 1048576).")
    ap.add_argument("--fill-byte", default="FF", help="Fill byte for gaps (default: FF).")
    ap.add_argument("--block-width", type=int, default=16, choices=[8, 16], help="Bytes per line (8 or 16). Default: 16.")
    ap.add_argument("-v", "--verbose", action="count", default=0, help="Increase diagnostics (-v, -vv).")
    args = ap.parse_args(argv)

    try:
        fill_byte = parse_hex_byte(args.fill_byte)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    try:
        mem_a, a_min, a_max, rec_a, map_a = parse_intel_hex(args.file_a, verbose=args.verbose)
        mem_b, b_min, b_max, rec_b, map_b = parse_intel_hex(args.file_b, verbose=args.verbose)

        lowest, highest = compute_unified_bounds(a_min, a_max, b_min, b_max)
        size = (highest - lowest) + 1

        if args.verbose >= 1:
            print(
                f"INFO: A: records={rec_a}, bytes_mapped={map_a}, data_range="
                f"{'none' if a_min is None else f'0x{a_min:08X}-0x{a_max:08X}'}",
                file=sys.stderr,
            )
            print(
                f"INFO: B: records={rec_b}, bytes_mapped={map_b}, data_range="
                f"{'none' if b_min is None else f'0x{b_min:08X}-0x{b_max:08X}'}",
                file=sys.stderr,
            )
            print(f"INFO: Unified range: 0x{lowest:08X} - 0x{highest:08X} (size {size} bytes)", file=sys.stderr)

        if size > args.max_size:
            print(
                "ERROR: Unified range exceeds maximum.\n"
                f"  lowest_address = 0x{lowest:08X}\n"
                f"  highest_address= 0x{highest:08X}\n"
                f"  size           = {size} bytes\n"
                f"  max_size       = {args.max_size} bytes",
                file=sys.stderr,
            )
            return EXIT_PARSE_OR_RANGE_ERROR

        layout_a = build_unified_layout(mem_a, lowest, highest, fill_byte=fill_byte)
        layout_b = build_unified_layout(mem_b, lowest, highest, fill_byte=fill_byte)

        # Dump both unified layouts
        out_a = derive_output_path(args.file_a)
        out_b = derive_output_path(args.file_b)
        dump_unified_layout(out_a, layout_a, source_path=args.file_a, lowest=lowest, highest=highest, width=args.block_width)
        dump_unified_layout(out_b, layout_b, source_path=args.file_b, lowest=lowest, highest=highest, width=args.block_width)

        if args.verbose >= 1:
            print(f"INFO: Wrote unified dump for A to: {out_a}", file=sys.stderr)
            print(f"INFO: Wrote unified dump for B to: {out_b}", file=sys.stderr)

        # Diff in-memory layouts
        if layout_a == layout_b:
            print("IDENTICAL")
            return EXIT_OK

        # Differences: print all differing lines with content
        diff_bytes, diff_lines = diff_and_print(layout_a, layout_b, lowest=lowest, width=args.block_width)

        # Minimal summary (kept on stderr to preserve "diff lines with content" on stdout)
        if args.verbose >= 1:
            print(f"INFO: Diff: differing_bytes={diff_bytes}, differing_lines={diff_lines}", file=sys.stderr)

        return EXIT_DIFF_FOUND

    except IntelHexParseError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_PARSE_OR_RANGE_ERROR
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_PARSE_OR_RANGE_ERROR
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_PARSE_OR_RANGE_ERROR


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
