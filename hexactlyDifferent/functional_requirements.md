# Requirements Specification (IREF-Style): ILITEK Intel HEX Firmware Diff Tool (Python 3)

## 1. Purpose

**REQ-PUR-001** The tool shall provide a deterministic, human-readable comparison of two **ILITEK touch controller firmware** images provided as **Intel HEX** files.
**REQ-PUR-002** The tool’s primary value shall be to compare firmware content by **addressed memory contents** (not by raw text line differences), minimizing noise caused by record ordering, gaps, and non-meaningful memory patterns.

## 2. Scope

**REQ-SCO-001** The tool shall be a **command-line Python 3 program** that:

1. parses two Intel HEX files,
2. builds a **unified address-based memory layout** for each,
3. performs a byte-level comparison over the unified address range, and
4. outputs a human-readable diff report to **stdout**.

**REQ-SCO-002** The tool shall support suppression of selected differences (blocked-memory patterns, configured ignore ranges), so that the report focuses on meaningful changes.

## 3. Definitions

**DEF-001 (Intel HEX)** ASCII text format representing binary data as records containing byte count, address, record type, data, and checksum.
**DEF-002 (Unified Memory Layout)** A normalized, random-access representation of firmware content where each absolute address in a defined range maps to exactly one byte value.
**DEF-003 (Blocked/Non-Meaningful Memory)** Address regions or bytes considered not semantically relevant for diffing (e.g., erased/unprogrammed flash bytes such as `0xFF`, or padding such as `0x00`) as configured.

## 4. Operating Environment

**REQ-ENV-001** The tool shall run on **Python 3.x** (Python 3.9+ recommended) using only the standard library unless otherwise justified.
**REQ-ENV-002** The tool shall run on Linux, macOS, and Windows, provided a Python 3 interpreter is available.

## 5. Inputs

### 5.1 Mandatory Inputs

**REQ-IN-001** The tool shall accept exactly two input file paths: `file_a.hex` and `file_b.hex`.

### 5.2 Optional Inputs

**REQ-IN-002** The tool shall optionally accept an ignore specification file path.
**REQ-IN-003** The tool shall optionally accept CLI flags controlling suppression and output verbosity.

## 6. Intel HEX Parsing

### 6.1 Record Support

**REQ-PAR-001** The tool shall support parsing of the following Intel HEX record types at minimum:

* Data record (type `00`)
* End-of-file record (type `01`)
* Extended Linear Address record (type `04`) to resolve 32-bit addressing
* Extended Segment Address record (type `02`) if present in input

**REQ-PAR-002** The tool shall correctly resolve absolute addresses using address extension records according to the Intel HEX specification.

### 6.2 Validation and Error Handling

**REQ-PAR-003** The tool shall validate record syntax (colon prefix, field lengths, hex decoding) and fail with a clear error message on malformed input.
**REQ-PAR-004** The tool shall validate record checksums by default and fail on mismatch (configurable via a flag; see Robustness Options).
**REQ-PAR-005** The tool shall report parsing errors with sufficient context (file name and line number).

### 6.3 Record Ordering

**REQ-PAR-006** The tool shall not assume records are ordered by address and shall correctly ingest data in any order.

### 6.4 Overlaps

**REQ-PAR-007** If multiple records write to the same absolute address, the tool shall apply a deterministic policy:

* Default: last write wins
* The tool shall emit a warning in verbose mode including address and record locations.

## 7. Unified Memory Layout Construction

### 7.1 Boundary Discovery

**REQ-MEM-001** Before allocating unified layouts, the tool shall scan both inputs and compute:

* `lowest_address`: minimum absolute data address found in either file
* `highest_address`: maximum absolute data address found in either file (inclusive)

**REQ-MEM-002** The unified comparison range shall be `[lowest_address, highest_address]` inclusive.
**REQ-MEM-003** The tool shall not assume the memory starts at address `0x00000000`.

### 7.2 Size Limits

**REQ-MEM-004** The tool shall enforce a default maximum unified range size of **1 MiB (1,048,576 bytes)**.
**REQ-MEM-005** If the computed range exceeds the configured maximum, the tool shall terminate with an error that includes:

* `lowest_address`, `highest_address`, computed size, and configured maximum.

### 7.3 Data Structure

**REQ-MEM-006** The tool shall represent each unified memory layout as a random-access byte container (e.g., `bytearray`) sized to the unified range length.

### 7.4 Gaps and Fill Behavior

**REQ-MEM-007** For addresses within the unified range not explicitly present in a file’s data records, the tool shall fill with a configurable fill byte.
**REQ-MEM-008** Default fill byte shall be `0xFF`.
**REQ-MEM-009** The fill strategy shall be applied consistently to both files.

## 8. Comparison and Diff Computation

### 8.1 Baseline Comparison

**REQ-DIF-001** The tool shall compare the two unified memory layouts byte-by-byte across the unified range.
**REQ-DIF-002** The tool shall identify and report all addresses where byte values differ, subject to suppression rules.

### 8.2 Grouping of Differences

**REQ-DIF-003** The tool shall group adjacent differing bytes into contiguous runs for reporting efficiency and readability.
**REQ-DIF-004** The tool shall render output in fixed-width blocks per line (hex-editor style).

### 8.3 Whitespace Handling (Clarified)

**REQ-DIF-005** The tool shall ignore extraneous whitespace in input lines during parsing (e.g., trailing spaces).
**REQ-DIF-006** The tool shall not produce a text-line diff of the Intel HEX files as the primary output; memory diff is authoritative.
**REQ-DIF-007** If a `--suppress-whitespace` flag is provided, it shall apply only to parsing tolerance and any optional text-oriented diagnostics, not to the memory diff semantics.

## 9. Suppression / Filtering

### 9.1 Blocked-Memory Suppression

**REQ-SUP-001** The tool shall support a suppression mode for blocked/non-meaningful memory via `--suppress-blocked-memory`.
**REQ-SUP-002** When enabled, the tool shall suppress reporting a difference at address `X` if both bytes are in the configured blocked set.
**REQ-SUP-003** The default blocked set shall be `{0xFF, 0x00}`.
**REQ-SUP-004** The blocked set shall be configurable via CLI (e.g., `--blocked-bytes FF,00`).
**REQ-SUP-005** The tool shall report suppression statistics in the summary (count suppressed by blocked-memory rule).

### 9.2 Ignore/Whitelist Specification

**REQ-SUP-006** The tool shall support ignoring explicitly specified addresses/ranges using `--ignore-file <path>`.
**REQ-SUP-007** The ignore file shall support:

* single address: `0x1234`
* inclusive range: `0x1000-0x10FF`
* comments beginning with `#`
* blank lines

**REQ-SUP-008** Any address within an ignored range shall not be reported as a difference.
**REQ-SUP-009** The tool shall report suppression statistics in the summary (count suppressed by ignore rules).

### 9.3 Output Modes

**REQ-SUP-010** The tool shall support:

* Full mode: report all differences after normalization (no suppression)
* Filtered mode: report differences after applying suppression rules
* Both mode: emit full and filtered reports in one run with clear section headers

## 10. Output Requirements

### 10.1 Human-Readable Diff Format

**REQ-OUT-001** The tool shall write its primary report to **stdout**.
**REQ-OUT-002** Each diff line shall include:

* the starting absolute address for the line,
* a block of bytes from file A in hex,
* a block of bytes from file B in hex,
* a per-byte indicator of differences within the block.

**REQ-OUT-003** Default block width shall be **16 bytes per line**, configurable (minimum support 8 and 16).
**REQ-OUT-004** Addresses shall be formatted consistently (e.g., `0x0001A2B0`), and the format shall be documented.

### 10.2 Summary

**REQ-OUT-005** The tool shall print a summary including at least:

* unified range start/end and total compared size
* number of differing bytes reported
* number of differing bytes suppressed (blocked-memory)
* number of differing bytes suppressed (ignore rules)

### 10.3 Diagnostics and Verbosity

**REQ-OUT-006** The tool shall provide verbosity levels that increase runtime diagnostics to stdout (or stderr as configured), including:

* boundaries discovered (`lowest_address`, `highest_address`, size)
* parsing progress (records processed, bytes mapped)
* overlap warnings
* suppression configuration (blocked set, ignore ranges loaded)
* comparison progress (optional, rate-limited)

**REQ-OUT-007** The tool shall provide a “very verbose” option suitable for troubleshooting that prints stepwise progress messages without overwhelming output by default (e.g., summary every N records/bytes).

## 11. CLI Interface

### 11.1 Basic Usage

**REQ-CLI-001** The tool shall support:
`hex_diff.py <file_a.hex> <file_b.hex> [options]`

### 11.2 Required Options

**REQ-CLI-002** The tool shall support the following options (names may be adjusted but must be documented and stable):

* `--mode {full,filtered,both}` (default: `filtered`)
* `--suppress-blocked-memory`
* `--blocked-bytes <csv>` (default: `FF,00`)
* `--ignore-file <path>`
* `--max-size <bytes>` (default: `1048576`)
* `--fill-byte <hex>` (default: `FF`)
* `--block-width <int>` (default: `16`)
* `--checksum {strict,off}` (default: `strict`)
* `-v/--verbose` (repeatable) and/or `--log-level {ERROR,WARN,INFO,DEBUG}`

### 11.3 Exit Codes

**REQ-CLI-003** Exit codes shall be:

* `0`: no differences reported under selected mode and no fatal errors
* `1`: differences reported under selected mode
* `2`: CLI usage/argument error
* `3`: parsing/validation error or range exceeds max size

## 12. Performance and Non-Functional Requirements

**REQ-NFR-001** The tool shall complete within **60 seconds** when comparing inputs whose unified range size is ≤ 1 MiB on a typical developer workstation.
**REQ-NFR-002** The tool shall operate in O(N) time with respect to unified range size, plus parsing overhead proportional to input record count.
**REQ-NFR-003** The tool shall limit memory use to a reasonable bound: two byte arrays of unified size plus overhead (for 1 MiB, approximately a few MiB total).
**REQ-NFR-004** The tool shall be implemented in a Pythonic, maintainable style with clear modular structure (parsing, normalization, suppression, diff formatting).

## 13. Documentation and Maintainability

**REQ-DOC-001** The tool shall include CLI `--help` text describing usage, options, and examples.
**REQ-DOC-002** The code shall include docstrings for public functions/modules and comments for non-obvious logic (address resolution, suppression rules).
**REQ-DOC-003** The repository/package (or script header) shall document:

* supported Intel HEX record types
* suppression semantics (exact rules)
* diff output format
* limitations and assumptions (max size default, fill byte default)

## 14. Acceptance Criteria

**ACC-001** Given two Intel HEX files representing the same memory contents but with different record ordering, the tool reports no differences in filtered mode with defaults.
**ACC-002** Given two Intel HEX files with a known byte change at address X, the tool reports the difference at address X in the output and exits with code `1`.
**ACC-003** With `--suppress-blocked-memory` enabled, differences where both bytes are within the configured blocked set are not reported, and suppression counters increase accordingly.
**ACC-004** With `--ignore-file` specifying a range containing X, differences at X are not reported, and ignore suppression counters increase accordingly.
**ACC-005** If unified range size exceeds `--max-size`, the tool fails with exit code `3` and prints computed boundaries and size.
**ACC-006** On malformed Intel HEX input (bad checksum in strict mode), the tool fails with exit code `3` and reports file + line number.

## 15. Out of Scope (Explicit)

**OOS-001** Generating patch/apply files (e.g., IPS/BSDIFF) is out of scope; the deliverable is a comparison/reporting tool.
**OOS-002** Device-specific disassembly or semantic interpretation of ILITEK firmware contents is out of scope; the tool operates on bytes and addresses only.
