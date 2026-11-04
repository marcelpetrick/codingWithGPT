# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the copied coding harness patch and failing-test scoring."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class CodingPatchTest(unittest.TestCase):
    def test_patch_applies_and_failing_tests_are_counted(self):
        root = Path(__file__).resolve().parent
        wrapper = (root / "coding-bench.sh").read_text()
        marker = "python3 - \"$out/cc-session-sandboxed.sh\" <<'PY'\n"
        patch_code = wrapper.split(marker, 1)[1].split("\nPY\n", 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "cc-session-sandboxed.sh"
            shutil.copy(
                root.parent
                / "ollamaClaudeCode_v4_tielCoder"
                / "cc-session-sandboxed.sh",
                target,
            )
            subprocess.run([sys.executable, "-c", patch_code, str(target)], check=True)
            subprocess.run(["bash", "-n", str(target)], check=True)
            patched = target.read_text()
            self.assertIn('git diff --name-only "$BASELINE" -- tests/', patched)
            self.assertIn(
                "{ python3 -m pytest -q -p no:cacheprovider hidden 2>&1 || true; }",
                patched,
            )
            shell = 'set -euo pipefail; value=$( { printf "16 passed, 2 failed\\n"; false; } || true ); printf "%s" "$value"'
            result = subprocess.run(
                ["bash", "-c", shell], check=True, text=True, capture_output=True
            )
            self.assertIn("16 passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
