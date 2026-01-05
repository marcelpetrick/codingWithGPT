import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "hexactlyDifferent.py"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()

    # Ensure repo root is importable so Python can find sitecustomize.py in subprocesses
    env["PYTHONPATH"] = str(REPO_ROOT) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )

    # Ensure subprocess coverage auto-start is enabled (inherited or default)
    env["COVERAGE_PROCESS_START"] = env.get("COVERAGE_PROCESS_START", ".coveragerc")

    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )

def _write_hex(path: Path, lines: list[str]) -> None:
    """Write ASCII Intel HEX lines to a file with trailing newline."""
    path.write_text("\n".join(lines) + "\n", encoding="ascii")

def test_identical_inputs_print_identical_and_exit_0(tmp_path: Path) -> None:
    # One data byte at 0x0000: 0xAA, checksum 0x55
    rec = ":01000000AA55"
    eof = ":00000001FF"

    a = tmp_path / "a.hex"
    b = tmp_path / "b.hex"
    _write_hex(a, [rec, eof])
    _write_hex(b, [rec, eof])

    proc = _run(str(a), str(b), cwd=tmp_path)

    assert proc.returncode == 0
    assert proc.stdout.strip() == "IDENTICAL"

    # Unified dumps should be created
    assert (tmp_path / "a.unified.txt").exists()
    assert (tmp_path / "b.unified.txt").exists()


def test_meaningful_diff_exit_1_and_prints_diff_lines(tmp_path: Path) -> None:
    # A: 0xAA at 0x0000
    # B: 0xAB at 0x0000
    a_rec = ":01000000AA55"
    b_rec = ":01000000AB54"
    eof = ":00000001FF"

    a = tmp_path / "a.hex"
    b = tmp_path / "b.hex"
    _write_hex(a, [a_rec, eof])
    _write_hex(b, [b_rec, eof])

    proc = _run(str(a), str(b), cwd=tmp_path)

    assert proc.returncode == 1
    # Should print an address line containing both hex bytes and a '^' marker
    assert "0x00000000:" in proc.stdout
    assert "AA" in proc.stdout and "AB" in proc.stdout
    assert "^" in proc.stdout


def test_suppress_erased_ff00_only_exit_0_and_prints_decision_and_lines(tmp_path: Path) -> None:
    # A: 0xFF at 0x0000 (checksum: 01+00+00+00+FF=0x100 => 0x00)
    # B: 0x00 at 0x0000 (checksum: 01+00+00+00+00=0x01 => 0xFF)
    a_rec = ":01000000FF00"
    b_rec = ":0100000000FF"
    eof = ":00000001FF"

    a = tmp_path / "a.hex"
    b = tmp_path / "b.hex"
    _write_hex(a, [a_rec, eof])
    _write_hex(b, [b_rec, eof])

    proc = _run(str(a), str(b), "--suppressErased", cwd=tmp_path)

    assert proc.returncode == 0
    # Script prints the suppressed diff lines section + decision message
    assert "SUPPRESSED_DIFF_LINES:" in proc.stdout
    assert "SUPPRESSED_ERASED:" in proc.stdout
    # Suppressed bytes are marked with '~'
    assert "~" in proc.stdout
    # It should still show the address line
    assert "0x00000000:" in proc.stdout


def test_suppress_erased_mixed_diffs_exit_1_and_prints_only_meaningful_lines(tmp_path: Path) -> None:
    # Two-byte records at 0x0000:
    # A: FF AA
    # B: 00 AB
    # At byte0: FF<->00 (suppressed)
    # At byte1: AA<->AB (meaningful)
    a_rec = ":02000000FFAA55"
    b_rec = ":0200000000AB53"
    eof = ":00000001FF"

    a = tmp_path / "a.hex"
    b = tmp_path / "b.hex"
    _write_hex(a, [a_rec, eof])
    _write_hex(b, [b_rec, eof])

    proc = _run(str(a), str(b), "--suppressErased", cwd=tmp_path)

    assert proc.returncode == 1
    # Address line printed
    assert "0x00000000:" in proc.stdout
    # Both markers should exist: '~' for suppressed, '^' for meaningful
    assert "~" in proc.stdout
    assert "^" in proc.stdout


def test_checksum_failure_exit_3_and_includes_file_and_line(tmp_path: Path) -> None:
    # Same as ":01000000AA55" but WRONG checksum (00)
    bad = ":01000000AA00"
    eof = ":00000001FF"

    a = tmp_path / "a.hex"
    b = tmp_path / "b.hex"
    _write_hex(a, [bad, eof])
    _write_hex(b, [":01000000AA55", eof])

    proc = _run(str(a), str(b), cwd=tmp_path)

    assert proc.returncode == 3
    # Error should include path and line number "a.hex:1:"
    assert "a.hex:1:" in proc.stderr
    assert "Checksum mismatch" in proc.stderr


def test_max_size_violation_exit_3(tmp_path: Path) -> None:
    # Create two data records far apart so unified size exceeds small max-size.
    # Record at 0x0000 and at 0x0100 => unified size 257 bytes.
    # We'll set --max-size 16 to force error.
    # Byte 0xAA at 0x0000: :01000000AA55
    # Byte 0xBB at 0x0100: ll=01 aaaa=0100 tt=00 dd=BB checksum: 01+01+00+00+BB=0xBD => 0x43
    rec0 = ":01000000AA55"
    rec1 = ":01010000BB43"
    eof = ":00000001FF"

    a = tmp_path / "a.hex"
    b = tmp_path / "b.hex"
    _write_hex(a, [rec0, eof])
    _write_hex(b, [rec1, eof])

    proc = _run(str(a), str(b), "--max-size", "16", cwd=tmp_path)

    assert proc.returncode == 3
    assert "Unified range exceeds maximum" in proc.stderr
    assert "lowest_address" in proc.stderr
    assert "highest_address" in proc.stderr


def test_overlap_last_write_wins_and_warns_in_verbose(tmp_path: Path) -> None:
    # Two overlapping one-byte records at same address 0x0000:
    # First: 0xAA, second: 0xAB (later should win).
    # We'll compare A vs B where B equals final value AB to ensure identical after overlap resolution.
    eof = ":00000001FF"
    a_lines = [
        ":01000000AA55",
        ":01000000AB54",
        eof,
    ]
    b_lines = [
        ":01000000AB54",
        eof,
    ]

    a = tmp_path / "a.hex"
    b = tmp_path / "b.hex"
    _write_hex(a, a_lines)
    _write_hex(b, b_lines)

    proc = _run(str(a), str(b), "-v", cwd=tmp_path)

    assert proc.returncode == 0
    assert proc.stdout.strip() == "IDENTICAL"
    # With -v, overlap should warn on stderr
    assert "WARN: overlap" in proc.stderr
