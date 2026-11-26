# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the unit suite against isolated, deliberate changes to the USB driver."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USB_MUTATIONS = (
    ("wrong color channel", '"yellow": 0x11', '"yellow": 0x12'),
    ("wrong report ID", "bytes((0, 0,", "bytes((1, 0,"),
    ("wrong return value", "    return 0\n", "    return 1\n"),
    ("never clear other lights", "if color not in colors:", "if False:"),
    ("accept short writes", "!= len(report)", "< 0"),
    (
        "skip cycle cleanup",
        "    finally:\n        set_lights(device, ())",
        "    finally:\n        pass",
    ),
)


MONITOR_MUTATIONS = (
    ("blocked beats waiting", '(State.BLOCKED, "red")', '(State.BLOCKED, "green")'),
    ("waiting turns yellow", '(State.WAITING, "yellow")', '(State.WAITING, "green")'),
    ("ignore reset time", "and resets_at > now", "and resets_at >= now"),
    (
        "inflate repeated color counts",
        "if shown is not None and shown != last_shown:",
        "if shown is not None:",
    ),
    (
        "count failed USB output",
        "\n                    shown = None\n",
        "\n                    shown = color\n",
    ),
    (
        "discard an observed quota block on a refresh error",
        "except READ_ERRORS:\n                    pass",
        "except READ_ERRORS:\n                    self.quota = {}",
    ),
    (
        "skip cleanup during the first USB write",
        "                attempted_output = True\n                try:\n                    show_color(color, args.usb_port)",
        "                try:\n                    show_color(color, args.usb_port)\n                    attempted_output = True",
    ),
)


def run_tests(directory):
    return subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=directory,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def main():
    baseline = run_tests(ROOT)
    if baseline.returncode:
        sys.exit(baseline.stderr)
    survivors = []
    targets = {
        "traffic_light.py": USB_MUTATIONS,
        "agent_status.py": MONITOR_MUTATIONS,
    }
    cases = [
        (filename, *mutation)
        for filename, mutations in targets.items()
        for mutation in mutations
    ]
    for filename, label, before, after in cases:
        source = (ROOT / filename).read_text(encoding="utf-8")
        if source.count(before) != 1:
            sys.exit(f"Expected one match for mutation {label}")
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "tests").mkdir()
            for production_file in targets:
                shutil.copyfile(ROOT / production_file, directory / production_file)
                test_file = Path("tests") / f"test_{production_file}"
                shutil.copyfile(ROOT / test_file, directory / test_file)
            (directory / filename).write_text(
                source.replace(before, after), encoding="utf-8"
            )
            result = run_tests(directory)
        if result.returncode == 0:
            survivors.append(label)
        elif "unittest.loader._FailedTest" not in result.stderr and (
            "FAIL: " in result.stderr or "ERROR: test_" in result.stderr
        ):
            print(f"Detected: {label}")
        else:
            sys.exit(result.stderr)
    if survivors:
        sys.exit(f"Survived: {', '.join(survivors)}")


if __name__ == "__main__":
    main()
