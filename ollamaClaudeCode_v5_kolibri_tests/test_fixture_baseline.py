# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that committed fixture changes remain visible to the scorer."""

import subprocess
import tempfile
from pathlib import Path
import unittest


class FixtureBaselineTest(unittest.TestCase):
    def test_committed_source_and_test_changes_remain_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def git(*args):
                return subprocess.run(
                    ["git", *args], cwd=root, check=True, capture_output=True, text=True
                ).stdout.strip()

            git("init", "-q")
            git("config", "user.name", "Fixture")
            git("config", "user.email", "fixture@example.invalid")
            (root / "tests").mkdir()
            (root / "stats.py").write_text("original\n")
            (root / "tests" / "test_stats.py").write_text("original\n")
            git("add", ".")
            git("commit", "-qm", "fixture")
            (root / "stats.py").write_text("fixed\n")
            (root / "tests" / "test_stats.py").write_text("changed\n")
            git("add", ".")
            git("commit", "-qm", "model change")
            baseline = git("rev-list", "--max-parents=0", "HEAD").splitlines()[-1]
            self.assertEqual(git("log", "-1", "--format=%s", baseline), "fixture")
            self.assertEqual(
                git("diff", "--name-only", baseline, "--", "stats.py"), "stats.py"
            )
            self.assertEqual(
                git("diff", "--name-only", baseline, "--", "tests/"),
                "tests/test_stats.py",
            )


if __name__ == "__main__":
    unittest.main()
