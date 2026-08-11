from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swearstats.cli import main


class CliTests(unittest.TestCase):
    def test_requires_at_least_one_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            status = main(
                [
                    "--claude-history",
                    str(root / "missing-claude"),
                    "--codex-history",
                    str(root / "missing-codex"),
                    "--output",
                    str(root / "report.html"),
                ]
            )
            self.assertEqual(status, 2)
            self.assertFalse((root / "report.html").exists())


if __name__ == "__main__":
    unittest.main()
