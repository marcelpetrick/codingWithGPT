import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "hexactlyDifferent.py"


def _write_hex(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def test_identical_inputs_print_identical_and_exit_0(tmp_path: Path) -> None:
    """
    Minimal end-to-end test:
    - Create two identical Intel HEX files containing a single data record + EOF.
    - Run the script via subprocess.
    - Assert stdout contains IDENTICAL and exit code is 0.
    """

    # Intel HEX record: 1 byte at address 0x0000 with value 0xAA
    # :ll aaaa tt dd cc
    # ll=01, aaaa=0000, tt=00, dd=AA, checksum=55
    rec = ":01000000AA55"
    eof = ":00000001FF"

    a = tmp_path / "a.hex"
    b = tmp_path / "b.hex"
    _write_hex(a, [rec, eof])
    _write_hex(b, [rec, eof])

    # Run script
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(a), str(b)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    assert proc.returncode == 0
    assert proc.stdout.strip() == "IDENTICAL"

    # Verify unified dumps were generated
    assert (tmp_path / "a.unified.txt").exists()
    assert (tmp_path / "b.unified.txt").exists()
