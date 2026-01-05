"""
hexactlyDifferent.py

ILITEK Intel HEX Firmware Normalizer + Diff (Python 3, stdlib only)

Overview
========
This tool provides a deterministic, address-based comparison of two Intel HEX firmware images.

High-level behavior
-------------------
1) Read exactly two Intel HEX file paths (A and B).
2) Parse both (record types 00/01/02/04) with strict checksum validation.
3) Discover unified bounds [lowest, highest] across BOTH inputs.
4) Enforce maximum unified size (default 1 MiB).
5) Build unified layouts for BOTH using the same fill byte.
6) Dump BOTH unified layouts to text files:
     <file_a_basename>.unified.txt
     <file_b_basename>.unified.txt
   - If output exists, remove it first.
   - Header is mandatory, exactly 4 lines; content begins at line 5.
7) Diff the unified layouts (address-based, not a text-line diff):
   - If identical: print "IDENTICAL" to stdout and exit 0.
   - If different: print differing lines (hex-editor style) to stdout and exit 1.

Diff output format (per differing line)
---------------------------------------
0xAAAAAAAA: <A hex bytes>  |<A ASCII>|   <B hex bytes>  |<B ASCII>|   <diff markers>

Where diff markers is a string of length N (block width):
  - '^' indicates a reported difference at that byte position.
  - '.' indicates equality at that position.
  - '~' indicates a suppressed FF<->00 difference when --suppressErased is active.

Block width
-----------
- Default 16, supports 8 or 16.

Suppression mode (--suppressErased)
-----------------------------------
Treat FF<->00 differences as “erased-marker noise” for purposes of reporting/exit code.

- If enabled and ALL differences are only FF<->00:
    * print the suppressed diff lines to stdout (so you can see where)
    * print a decision message to stdout
    * exit 0 (treated as identical)
- If enabled and there are other differences:
    * print only lines containing non-suppressed differences
    * exit 1

Domain notes:
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

# -----------------------------------------------------------------------------
# Exit codes (aligned with earlier requirements / typical CLI practice)
# -----------------------------------------------------------------------------
EXIT_OK = 0
EXIT_DIFF_FOUND = 1
EXIT_USAGE_ERROR = 2
EXIT_PARSE_OR_RANGE_ERROR = 3


# -----------------------------------------------------------------------------
# Helper data structures / exceptions
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class WriteOrigin:
    """
    @brief Stores provenance for a byte write during Intel HEX ingestion.
    @details Used only for verbose overlap warnings ("last write wins").
    """

    file_path: str
    """@brief Source file path that wrote the byte."""

    line_no: int
    """@brief Line number in the source file that wrote the byte."""


class IntelHexParseError(RuntimeError):
    """
    @brief Exception raised for Intel HEX parsing/validation errors.

    @details
    This exception includes file path and line number context in the message,
    satisfying the requirement to report parsing errors with sufficient context.
    """

    def __init__(self, message: str, file_path: str, line_no: int):
        """
        @param message Human-readable error message.
        @param file_path Path to the Intel HEX file being parsed.
        @param line_no 1-based line number where the error occurred. May be 0 if unknown.
        """
        super().__init__(f"{file_path}:{line_no}: {message}")
        self.file_path = file_path
        self.line_no = line_no


# -----------------------------------------------------------------------------
# Intel HEX parsing primitives
# -----------------------------------------------------------------------------
def _hex_to_int(h: str, file_path: str, line_no: int) -> int:
    """
    @brief Convert a hex string into an integer with contextual error reporting.

    @param h Hex string (no 0x prefix required).
    @param file_path Current file being parsed (for context).
    @param line_no Current line number (for context).
    @return Parsed integer value.
    @raises IntelHexParseError If conversion fails.
    """
    try:
        return int(h, 16)
    except ValueError:
        raise IntelHexParseError(f"Invalid hex value: {h!r}", file_path, line_no)


def _parse_record(line: str, file_path: str, line_no: int) -> Tuple[int, int, int, bytes, int]:
    """
    @brief Parse a single Intel HEX record line with strict validation.

    @details
    The Intel HEX record format is:
      :llaaaatt[dd...]cc
    where:
      - ll   = byte count
      - aaaa = 16-bit address
      - tt   = record type
      - dd   = data bytes (ll bytes)
      - cc   = checksum

    Validation performed:
      - leading ':' required
      - even number of hex characters
      - byte count matches data length
      - checksum verified (sum of all bytes including checksum == 0 mod 256)

    @param line Raw input line.
    @param file_path Source file path for diagnostics.
    @param line_no 1-based line number for diagnostics.
    @return Tuple (byte_count, address16, record_type, data_bytes, checksum).
    @raises IntelHexParseError On malformed syntax or checksum mismatch.
    """
    s = line.strip()  # tolerate trailing/leading whitespace
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

    # Strict checksum validation:
    # The low 8 bits of the sum of all bytes in the record (including checksum) must be 0.
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
    @brief Parse an Intel HEX file into an absolute-address memory map.

    @details
    Supported record types:
      - 00: Data
      - 01: End-of-file
      - 02: Extended Segment Address (base = value << 4)
      - 04: Extended Linear Address  (base = value << 16)

    Address resolution:
      - The current "base" is updated by record types 02/04.
      - Data record absolute address = base + address16 + data_index

    Overlap policy:
      - "Last write wins" deterministically.
      - If verbose >= 1, overlaps produce warnings with both write locations.

    Blank lines:
      - Ignored (tolerated), to accommodate some HEX exporters.

    @param file_path Path to the Intel HEX file.
    @param verbose Verbosity level; >=1 enables overlap warnings, >=2 logs ignored record types.
    @return
      (memory_map, min_addr, max_addr, records_processed, bytes_mapped)
      - memory_map: dict[absolute_address] = byte_value (0..255)
      - min_addr/max_addr: min/max absolute data addresses observed (None if no data)
      - records_processed: count of parsed records (non-empty lines)
      - bytes_mapped: number of data bytes written into memory_map (including overwrites)
    @raises IntelHexParseError On file errors, malformed records, or checksum failure.
    """
    memory: Dict[int, int] = {}
    origins: Dict[int, WriteOrigin] = {}

    base = 0  # updated by type 02/04 records
    min_addr: Optional[int] = None
    max_addr: Optional[int] = None
    records = 0
    mapped = 0

    try:
        with open(file_path, "r", encoding="ascii", errors="strict") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.rstrip("\n")
                if not line.strip():
                    # Tolerance choice: ignore blank lines.
                    continue

                byte_count, addr16, rectype, data, _ck = _parse_record(line, file_path, line_no)
                records += 1

                if rectype == 0x00:  # Data record
                    abs_start = base + addr16
                    for i, b in enumerate(data):
                        a = abs_start + i

                        # Overlap warning (deterministic last-write-wins policy).
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

                elif rectype == 0x01:  # End-of-file
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
                    # Not required for the current phase; ignore other record types.
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


# -----------------------------------------------------------------------------
# Unified layout construction
# -----------------------------------------------------------------------------
def compute_unified_bounds(
    a_min: Optional[int],
    a_max: Optional[int],
    b_min: Optional[int],
    b_max: Optional[int],
) -> Tuple[int, int]:
    """
    @brief Compute the unified address range across both inputs.

    @details
    The unified comparison range is the inclusive interval:
      [lowest_address, highest_address]
    where lowest/highest are computed across both A and B data ranges.

    @param a_min Minimum absolute address in file A (or None if no data).
    @param a_max Maximum absolute address in file A (or None if no data).
    @param b_min Minimum absolute address in file B (or None if no data).
    @param b_max Maximum absolute address in file B (or None if no data).
    @return (lowest_address, highest_address), inclusive.
    @raises ValueError If neither file contains any data records.
    """
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
    """
    @brief Build a random-access unified layout for a single input file.

    @details
    A unified layout is a contiguous bytearray representing every address
    in the unified range [lowest, highest]. Any address not present in the
    input's data records is filled with fill_byte.

    @param memory_map Dict mapping absolute addresses to byte values for one file.
    @param lowest Inclusive start address of the unified range.
    @param highest Inclusive end address of the unified range.
    @param fill_byte Fill value used for gaps (0..255).
    @return Unified memory layout as a bytearray of length (highest-lowest+1).
    """
    size = (highest - lowest) + 1
    buf = bytearray([fill_byte] * size)
    for addr, val in memory_map.items():
        if lowest <= addr <= highest:
            buf[addr - lowest] = val
    return buf


# -----------------------------------------------------------------------------
# Unified layout dump formatting
# -----------------------------------------------------------------------------
def derive_output_path(src_file: str) -> str:
    """
    @brief Derive the output path for a unified dump from an input path.

    @details
    If src_file ends with ".hex" (case-insensitive), replace the extension with ".unified.txt".
    Otherwise, append ".unified.txt".

    @param src_file Input file path.
    @return Output file path for the unified dump.
    """
    base, ext = os.path.splitext(src_file)
    if ext.lower() == ".hex":
        return base + ".unified.txt"
    return src_file + ".unified.txt"


def mandatory_header_lines(source_path: str, lowest: int, highest: int, size: int) -> List[str]:
    """
    @brief Create the mandatory 4-line header for unified dump files.

    @details
    Header requirements:
      - Exactly 4 lines
      - Content begins at line 5 (no blank line before content)

    @param source_path Original Intel HEX file path.
    @param lowest Unified range start address.
    @param highest Unified range end address.
    @param size Unified size in bytes.
    @return List of exactly four header lines (strings without trailing newline).
    """
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
    """
    @brief Write a unified layout to a text file in a deterministic hex+ASCII format.

    @details
    Output file rules:
      - If out_path exists, remove it before writing.
      - Write exactly 4 header lines; content begins at line 5.
      - For each line, print:
          0xAAAAAAAA: <hex bytes>  |<ASCII>|
        where <hex bytes> is padded to the chosen width.

    @param out_path Output file path to write.
    @param layout Unified layout to dump (bytearray).
    @param source_path Source file path used for header "SOURCE".
    @param lowest Unified range start address.
    @param highest Unified range end address.
    @param width Number of bytes per output line (8 or 16).
    @raises RuntimeError If an existing output file cannot be removed.
    """
    def to_ascii(b: int) -> str:
        """
        @brief Convert a byte to printable ASCII for dump visualization.
        @param b Byte value (0..255).
        @return Printable ASCII char, or '.' for non-printable bytes.
        """
        return chr(b) if 0x20 <= b <= 0x7E else "."

    # Remove existing output file (requirement).
    try:
        if os.path.exists(out_path):
            os.remove(out_path)
    except OSError as e:
        raise RuntimeError(f"Failed to remove existing output file {out_path!r}: {e}") from e

    size = len(layout)
    header = mandatory_header_lines(source_path, lowest, highest, size)

    with open(out_path, "w", encoding="utf-8", newline="\n") as w:
        # Header lines 1-4
        for line in header:
            w.write(line + "\n")

        # Content starts at line 5 (no blank line inserted)
        for offset in range(0, size, width):
            addr = lowest + offset
            chunk = layout[offset: offset + width]

            hex_bytes = " ".join(f"{b:02X}" for b in chunk)
            if len(chunk) < width:
                # Keep columns aligned on final partial line.
                hex_bytes += "   " * (width - len(chunk))

            ascii_col = "".join(to_ascii(b) for b in chunk)
            w.write(f"0x{addr:08X}: {hex_bytes}  |{ascii_col}|\n")


# -----------------------------------------------------------------------------
# Diff formatting primitives
# -----------------------------------------------------------------------------
def _ascii_of_chunk(chunk: bytes) -> str:
    """
    @brief Render ASCII visualization for a block of bytes.
    @param chunk Byte sequence.
    @return ASCII string where non-printable bytes are shown as '.'.
    """
    return "".join(chr(b) if 0x20 <= b <= 0x7E else "." for b in chunk)


def _hex_bytes(chunk: bytes, width: int) -> str:
    """
    @brief Render a hex byte string for a block, padded to a fixed width.

    @param chunk Byte sequence for this block (may be shorter than width at EOF).
    @param width Desired display width (8 or 16).
    @return Space-separated hex string padded for alignment.
    """
    s = " ".join(f"{b:02X}" for b in chunk)
    if len(chunk) < width:
        s += "   " * (width - len(chunk))
    return s


def _is_ff00_pair(a: int, b: int) -> bool:
    """
    @brief Determine whether a difference is the special FF<->00 “erased-marker” pair.

    @param a Byte from layout A.
    @param b Byte from layout B.
    @return True if bytes are exactly (FF,00) or (00,FF), else False.
    """
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
    @brief Compare two unified layouts and print differing lines in hex-editor style.

    Printing rules
    --------------
    - Without suppression:
        Print every line (block) that contains any difference.
    - With --suppressErased:
        - Print only lines that contain at least one non-suppressed difference.
        - If print_suppressed_only_lines is True, also print lines that contain ONLY suppressed FF<->00 diffs.

    Marker column
    -------------
    - '^' for reported differences (non-suppressed).
    - '~' for suppressed FF<->00 differences (only when suppress_erased is True).
    - '.' for equal bytes.

    @param layout_a Unified layout A (bytearray).
    @param layout_b Unified layout B (bytearray).
    @param lowest Unified start address (used to label printed addresses).
    @param width Bytes per printed line (8 or 16).
    @param suppress_erased Enable FF<->00 suppression logic.
    @param print_suppressed_only_lines When True and suppress_erased is enabled, also print suppressed-only lines.
    @return
      (total_diff_bytes, suppressed_ff00_bytes, reported_diff_bytes, printed_lines)
      - total_diff_bytes: count of all byte positions where A != B
      - suppressed_ff00_bytes: count of byte positions suppressed by FF<->00 rule
      - reported_diff_bytes: count of byte positions reported as meaningful diffs
      - printed_lines: number of output lines printed by this function
    @raises RuntimeError If layouts differ in length (should not occur if unified correctly).
    """
    if len(layout_a) != len(layout_b):
        raise RuntimeError("Internal error: unified layouts have different lengths.")

    size = len(layout_a)
    total_diff_bytes = 0
    suppressed_ff00_bytes = 0
    reported_diff_bytes = 0
    printed_lines = 0

    for offset in range(0, size, width):
        a_chunk = bytes(layout_a[offset: offset + width])
        b_chunk = bytes(layout_b[offset: offset + width])

        # Fast path: identical block
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
                markers.append("~")
            else:
                line_has_reportable = True
                reported_diff_bytes += 1
                markers.append("^")

        # Apply suppression printing rules.
        if suppress_erased:
            if not line_has_reportable and not (print_suppressed_only_lines and line_has_suppressed):
                continue

        printed_lines += 1
        addr = lowest + offset

        a_hex = _hex_bytes(a_chunk, width)
        b_hex = _hex_bytes(b_chunk, width)
        a_ascii = _ascii_of_chunk(a_chunk)
        b_ascii = _ascii_of_chunk(b_chunk)

        # Marker string is padded to width for alignment on final partial line.
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


# -----------------------------------------------------------------------------
# CLI parsing helpers
# -----------------------------------------------------------------------------
def parse_hex_byte(s: str) -> int:
    """
    @brief Parse a CLI hex byte value.

    @details
    Accepts either "FF" or "0xFF" form. Exactly one byte is required.

    @param s Input string from CLI.
    @return Integer byte value 0..255.
    @raises ValueError If input does not represent exactly one byte.
    """
    s = s.strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    if len(s) != 2:
        raise ValueError("Fill byte must be exactly one byte (e.g., FF or 0xFF).")
    v = int(s, 16)
    if not (0 <= v <= 0xFF):
        raise ValueError("Fill byte out of range.")
    return v


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------
def main(argv: List[str]) -> int:
    """
    @brief Program entry point implementing the end-to-end workflow.

    Workflow:
      1) Parse CLI arguments
      2) Parse both Intel HEX files into memory maps
      3) Compute unified bounds and validate size
      4) Build unified layouts
      5) Dump both layouts to .unified.txt outputs
      6) Diff layouts and apply --suppressErased decision logic

    Exit codes:
      - 0: identical or treated-as-identical due to --suppressErased
      - 1: meaningful differences reported
      - 2: CLI usage error
      - 3: parse/validation/range errors

    @param argv CLI arguments (excluding program name).
    @return Process exit code (int).
    """
    ap = argparse.ArgumentParser(
        prog="hexactlyDifferent.py",
        description="Unify BOTH Intel HEX inputs into address-based layouts, dump BOTH, then diff them.",
    )
    ap.add_argument("file_a", help="Path to file A (Intel HEX).")
    ap.add_argument("file_b", help="Path to file B (Intel HEX).")
    ap.add_argument(
        "--max-size",
        type=int,
        default=1048576,
        help="Maximum unified range size in bytes (default: 1048576).",
    )
    ap.add_argument("--fill-byte", default="FF", help="Fill byte for gaps (default: FF).")
    ap.add_argument(
        "--block-width",
        type=int,
        default=16,
        choices=[8, 16],
        help="Bytes per line (8 or 16). Default: 16.",
    )
    ap.add_argument(
        "--suppressErased",
        action="store_true",
        help="Suppress FF<->00 differences; if all diffs are only FF<->00, exit 0 and still show the diff.",
    )
    ap.add_argument("-v", "--verbose", action="count", default=0, help="Increase diagnostics (-v, -vv).")
    args = ap.parse_args(argv)

    # Parse fill-byte option early to provide a clean usage error.
    try:
        fill_byte = parse_hex_byte(args.fill_byte)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    try:
        # Parse both inputs into absolute-address maps.
        mem_a, a_min, a_max, rec_a, map_a = parse_intel_hex(args.file_a, verbose=args.verbose)
        mem_b, b_min, b_max, rec_b, map_b = parse_intel_hex(args.file_b, verbose=args.verbose)

        # Compute unified range and size.
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

        # Enforce maximum unified size.
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

        # Build unified layouts for both inputs.
        layout_a = build_unified_layout(mem_a, lowest, highest, fill_byte=fill_byte)
        layout_b = build_unified_layout(mem_b, lowest, highest, fill_byte=fill_byte)

        # Dump unified layouts to disk (always).
        out_a = derive_output_path(args.file_a)
        out_b = derive_output_path(args.file_b)
        dump_unified_layout(
            out_a,
            layout_a,
            source_path=args.file_a,
            lowest=lowest,
            highest=highest,
            width=args.block_width,
        )
        dump_unified_layout(
            out_b,
            layout_b,
            source_path=args.file_b,
            lowest=lowest,
            highest=highest,
            width=args.block_width,
        )

        if args.verbose >= 1:
            print(f"INFO: Wrote unified dump for A to: {out_a}", file=sys.stderr)
            print(f"INFO: Wrote unified dump for B to: {out_b}", file=sys.stderr)

        # Identical after normalization -> exit 0.
        if layout_a == layout_b:
            print("IDENTICAL")
            return EXIT_OK

        # First pass printing:
        # - If suppression is OFF: prints all differing lines.
        # - If suppression is ON: prints only lines with reportable diffs.
        total_diff, suppressed_ff00, reported_diff, printed_lines = diff_and_print(
            layout_a,
            layout_b,
            lowest=lowest,
            width=args.block_width,
            suppress_erased=args.suppressErased,
            print_suppressed_only_lines=False,
        )

        # If suppressErased is enabled and we suppressed ALL differences, show the suppressed lines too
        # and treat as identical (exit 0).
        if args.suppressErased and total_diff > 0 and reported_diff == 0:
            print("SUPPRESSED_DIFF_LINES:")
            diff_and_print(
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

        # Otherwise: meaningful differences exist.
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
        # Parsing/validation errors must include file+line context.
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_PARSE_OR_RANGE_ERROR
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_PARSE_OR_RANGE_ERROR
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_PARSE_OR_RANGE_ERROR


if __name__ == "__main__":
    # Pass sys.argv[1:] to keep main() testable.
    sys.exit(main(sys.argv[1:]))
