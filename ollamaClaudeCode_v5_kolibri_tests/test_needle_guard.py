# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reject an uncalibrated retrieval depth before touching the server."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class NeedleGuardTest(unittest.TestCase):
    def test_rejects_overflow_depth_before_creating_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "needle-probe.sh"
            shutil.copy(Path(__file__).with_name("needle-probe.sh"), script)
            result = subprocess.run(
                ["bash", str(script), "test", "80000"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("calibrated", result.stderr)
            self.assertFalse((root / "results").exists())


if __name__ == "__main__":
    unittest.main()
