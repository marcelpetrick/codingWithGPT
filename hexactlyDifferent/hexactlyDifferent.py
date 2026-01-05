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

Adds:
  --suppressErased
    Treat FF<->00 differences as “erased-marker noise” for purposes of reporting/exit code.
    - If enabled and ALL differences are only FF<->00, then:
        * print a decision message to stdout
        * exit 0
    - If enabled and there are other differences:
        * print only lines containing non-suppressed differences
        * exit 1
           * ALSO print the suppressed diff lines to stdout (so you can see where)

Notes (per your domain rules):
  - 0xFF may mean “erased / unused”
  - 0x00 always means “explicitly programmed”
  This option is intentionally narrow: it suppresses only the specific FF<->00 pair.
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
    s = line.strip()
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
                    continue

                byte_count, addr16, rectype, data, _ck = _parse_record(line, file_path, line_no)
                records += 1

                if rectype == 0x00:
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

                elif rectype == 0x01:
                    break

                elif rectype == 0x04:
                    if byte_count != 2:
                        raise IntelHexParseError("Type 04 record must have byte count 2.", file_path, line_no)
                    upper = (data[0] << 8) | data[1]
                    base = upper << 16

                elif rectype == 0x02:
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


def _is_ff00_pair(a: int, b: int) -> bool:
    return (a == 0xFF and b == 0x00) or (a == 0x00 and b == 0xFF)


def diff_and_print(
    layout_a: bytearray,
    layout_b: bytearray,
    *,
    lowest: int,
    width: int,
    suppress_erased: bool,
    print_suppressed_only_lines: bool,
) -> Tuple[int, int, int, int]:
    """
    Prints differing lines.

    If suppress_erased is True:
      - Normally prints only lines that have at least one non-suppressed difference.
      - If print_suppressed_only_lines is True, also prints lines that contain only suppressed diffs.

    Returns:
      (total_diff_bytes, suppressed_ff00_bytes, reported_diff_bytes, printed_lines)
    """
    if len(layout_a) != len(layout_b):
        raise RuntimeError("Internal error: unified layouts have different lengths.")

    size = len(layout_a)
    total_diff_bytes = 0
    suppressed_ff00_bytes = 0
    reported_diff_bytes = 0
    printed_lines = 0

    for offset in range(0, size, width):
        a_chunk = bytes(layout_a[offset : offset + width])
        b_chunk = bytes(layout_b[offset : offset + width])
        if a_chunk == b_chunk:
            continue

        markers: List[str] = []
        line_has_reportable = False
        line_has_suppressed = False

        for i in range(len(a_chunk)):
            if a_chunk[i] == b_chunk[i]:
                markers.append(".")
                continue

            total_diff_bytes += 1

            if suppress_erased and _is_ff00_pair(a_chunk[i], b_chunk[i]):
                suppressed_ff00_bytes += 1
                line_has_suppressed = True
                markers.append("~")  # mark suppressed diffs explicitly
            else:
                line_has_reportable = True
                reported_diff_bytes += 1
                markers.append("^")

        # printing rules
        if suppress_erased:
            if not line_has_reportable and not (print_suppressed_only_lines and line_has_suppressed):
                continue

        printed_lines += 1
        addr = lowest + offset

        a_hex = _hex_bytes(a_chunk, width)
        b_hex = _hex_bytes(b_chunk, width)
        a_ascii = _ascii_of_chunk(a_chunk)
        b_ascii = _ascii_of_chunk(b_chunk)

        if len(a_chunk) < width:
            markers.extend(" " * (width - len(a_chunk)))

        marker_str = "".join(markers)
        print(
            f"0x{addr:08X}: "
            f"{a_hex}  |{a_ascii}|   "
            f"{b_hex}  |{b_ascii}|   "
            f"{marker_str}"
        )

    return total_diff_bytes, suppressed_ff00_bytes, reported_diff_bytes, printed_lines


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
    ap.add_argument(
        "--suppressErased",
        action="store_true",
        help="Suppress FF<->00 differences; if all diffs are only FF<->00, exit 0 and still show the diff.",
    )
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

        # Dump both unified layouts (always)
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

        # First pass: print only reportable lines (or also suppressed-only lines if we end up suppressing everything)
        total_diff, suppressed_ff00, reported_diff, printed_lines = diff_and_print(
            layout_a,
            layout_b,
            lowest=lowest,
            width=args.block_width,
            suppress_erased=args.suppressErased,
            print_suppressed_only_lines=False,
        )

        if args.suppressErased and total_diff > 0 and reported_diff == 0:
            # In this case, we suppressed everything; now show those suppressed-only lines too.
            print("SUPPRESSED_DIFF_LINES:")
            _total2, _supp2, _rep2, _lines2 = diff_and_print(
                layout_a,
                layout_b,
                lowest=lowest,
                width=args.block_width,
                suppress_erased=True,
                print_suppressed_only_lines=True,
            )
            print(
                f"SUPPRESSED_ERASED: differences detected but all are FF<->00 only "
                f"(suppressed_bytes={suppressed_ff00}). Treating as IDENTICAL."
            )
            return EXIT_OK

        if args.verbose >= 1:
            if args.suppressErased:
                print(
                    f"INFO: Diff: total_diff_bytes={total_diff}, suppressed_ff00_bytes={suppressed_ff00}, "
                    f"reported_diff_bytes={reported_diff}, printed_lines={printed_lines}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"INFO: Diff: differing_bytes={total_diff}, printed_lines={printed_lines}",
                    file=sys.stderr,
                )

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
