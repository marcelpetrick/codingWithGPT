## hex file compariser (based on unified memory layout) - `hexactlyDifferent.py`

* requirements collection: see `functional_requirements.md`

Deterministic, address-based comparison tool for **ILITEK touch controller firmware** provided as **Intel HEX** files. The tool normalizes both inputs into unified, random-access memory layouts (gap-filled), writes those layouts to text dumps, and then performs a byte-wise diff over the unified address range.

## Purpose

Intel HEX files are line-oriented, but record ordering, gaps, and formatting differences can create noisy diffs. This tool compares firmware **by resolved absolute memory contents**, not by textual line differences, making output stable and meaningful for firmware review.

Key properties:

* Address-based normalization (records may be unordered)
* Strict checksum validation
* Deterministic overlap policy (last write wins)
* Human-readable hex-editor-style diff output
* Optional suppression of `FF <-> 00` differences via `--suppressErased` (domain-specific “erased-marker noise”)

## Requirements / Environment

* Python 3.x (tested with Python 3.13)
* Standard library only
* Runs on Linux (and maybe macOS/Windows)

## Installation

No installation required.

```bash
chmod +x hexactlyDifferent.py
```

Or run directly:

```bash
python3 hexactlyDifferent.py --help
```

## Usage

```bash
python3 hexactlyDifferent.py <file_a.hex> <file_b.hex> [options]
```

Common options:

* `-v, --verbose` (repeatable): prints diagnostics to `stderr` (ranges, counts, overlap warnings)
* `--block-width {8,16}`: output width (default: 16)
* `--fill-byte FF|0xFF`: fill value for gaps (default: `FF`)
* `--max-size <bytes>`: max unified range size in bytes (default: `1048576`)
* `--suppressErased`: treat `FF <-> 00` diffs as “erased-marker noise” for exit code decision (details below)

## tl;dr: diff check example
```
  python3 hexactlyDifferent.py testFiles/expo_ili.hex testFiles/2025-11-12_14-14-07_ili2315.hex -v --suppressErased
INFO: A: records=4008, bytes_mapped=64004, data_range=0x00000000-0x0001F43F
INFO: B: records=4043, bytes_mapped=64548, data_range=0x00000000-0x0001FDFF
INFO: Unified range: 0x00000000 - 0x0001FDFF (size 130560 bytes)
INFO: Wrote unified dump for A to: testFiles/expo_ili.unified.txt
INFO: Wrote unified dump for B to: testFiles/2025-11-12_14-14-07_ili2315.unified.txt
SUPPRESSED_DIFF_LINES:
0x0001F060: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF  |................|   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  |................|   ~~~~~~~~~~~~~~~~
0x0001F230: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF  |................|   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  |................|   ~~~~~~~~~~~~~~~~
SUPPRESSED_ERASED: differences detected but all are FF<->00 only (suppressed_bytes=32). Treating as IDENTICAL.
  echo $?
0
```

## Workflow (What the script does)

1. **Read inputs**

   * Accepts exactly two Intel HEX file paths: `file_a` and `file_b`.

2. **Parse Intel HEX**

   * Supports record types:

     * `00` Data
     * `01` End-of-file
     * `02` Extended Segment Address (base = value << 4)
     * `04` Extended Linear Address  (base = value << 16)
   * Validates record structure and **checksums strictly**.
   * Tolerates blank lines.
   * Does **not** require records to be ordered.
   * Overlaps are resolved deterministically: **last write wins**.

     * With `-v`, overlaps emit warnings to `stderr` including address and source locations.

3. **Discover unified bounds**

   * Computes a single inclusive range `[lowest_address, highest_address]` across **both** inputs.

4. **Enforce maximum range**

   * If `(highest - lowest + 1) > --max-size`, exits with code `3` and prints boundaries to `stderr`.

5. **Build unified memory layouts**

   * Creates two `bytearray` buffers, one per input, of size `(highest - lowest + 1)`.
   * For addresses missing in a file, fills with `--fill-byte` (default `0xFF`).

6. **Dump both unified layouts**

   * Writes:

     * `<file_a_basename>.unified.txt`
     * `<file_b_basename>.unified.txt`
   * If a dump file already exists, it is **removed first**.
   * Dump header is **mandatory** and **exactly 4 lines**.
   * Content begins at **line 5**.

7. **Diff the unified layouts**

   * If layouts are identical: prints `IDENTICAL` to `stdout`, exits `0`.
   * Otherwise: prints differing lines to `stdout` in hex-editor style, exits `1`.
   * With `--suppressErased`: `FF <-> 00` differences can be suppressed for the “identical vs different” decision (see below).

## Output Files: Unified Dumps

Each unified dump file begins with exactly 4 header lines:

1. `# UNIFIED_MEMORY_LAYOUT v1`
2. `# SOURCE <path>`
3. `# RANGE 0xAAAAAAAA 0xBBBBBBBB SIZE <N>`
4. `# FORMAT: 0xAAAAAAAA: <hex bytes>  |<ASCII>|   (CONTENT_STARTS_AT_LINE 5)`

Content lines start at line 5 and are formatted like:

```
0x00000000: 12 34 56 78 ...  |....|
```

## Diff Output Format (stdout)

Each printed line represents one differing block (width is 8 or 16 bytes):

```
0xAAAAAAAA: <A hex bytes>  |<A ASCII>|   <B hex bytes>  |<B ASCII>|   <markers>
```

Markers are per-byte indicators:

* `^` : reported difference at that byte position
* `.` : bytes equal
* `~` : suppressed `FF <-> 00` difference when `--suppressErased` is active

### Example: Normal diff (exit code 1)

```
0x0001A2B0: 10 20 30 40 FF FF FF FF  00 11 22 33 44 55 66 77  |. 0@.... .."3DUfw|   10 20 30 40 00 00 00 00  00 11 22 33 44 55 66 77  |. 0@.... .."3DUfw|   ....^^^^........
```

### Example: Identical (exit code 0)

```
IDENTICAL
```

## `--suppressErased` Semantics

This option is intentionally narrow and domain-specific:

* It treats **only** `FF <-> 00` byte differences as “erased-marker noise.”
* Domain notes:

  * `0xFF` may mean “erased / unused”
  * `0x00` always means “explicitly programmed”
* The tool does **not** attempt broader semantics (e.g., `FF <-> FF`, `00 <-> 00` are just equal).

Behavior:

* If there are differences, but **all** differences are `FF <-> 00`:

  * Prints:

    * `SUPPRESSED_DIFF_LINES:` followed by the suppressed-only diff lines (marked with `~`)
    * A decision line like:
      `SUPPRESSED_ERASED: differences detected but all are FF<->00 only (suppressed_bytes=...). Treating as IDENTICAL.`
  * Exits `0`.

* If there are differences and **some** are not `FF <-> 00`:

  * Prints only lines containing at least one non-suppressed difference.
  * Exits `1`.

### Example: Suppressed erased-only diff (exit code 0)

```
SUPPRESSED_DIFF_LINES:
0x00001000: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF  |................|   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  |................|   ~~~~~~~~~~~~~~~~
SUPPRESSED_ERASED: differences detected but all are FF<->00 only (suppressed_bytes=16). Treating as IDENTICAL.
```

## Exit Codes

* `0`: identical after normalization, or treated as identical due to `--suppressErased`
* `1`: meaningful differences reported
* `2`: CLI usage error (invalid arguments/options)
* `3`: parsing/validation error, or unified range exceeds `--max-size`

## Testing

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install pytest coverage pytest-cov
```

Invoke with:
`pytest -v`

### Coverage

```
COVERAGE_PROCESS_START=.coveragerc pytest
coverage combine
coverage html
coverage report -m
```

Check directory  `htmlcov` for the output.

## License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.

## Contact

For issues, questions, or contributions: `mail@marcelpetrick.`
