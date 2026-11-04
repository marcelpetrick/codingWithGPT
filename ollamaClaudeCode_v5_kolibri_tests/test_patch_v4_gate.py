# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test that copied v4 gates enforce the stricter scoring rules."""

import importlib.util
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

import patch_v4_gate

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "ollamaClaudeCode_v4_tielCoder" / "gate-rerun.py"


class PatchGateTest(unittest.TestCase):
    def test_patch_enforces_t1_and_t5(self):
        source = SOURCE.read_text()
        patched = patch_v4_gate.apply(source, adaptive=True)
        self.assertIn('"thinking": {"type": "adaptive"}', patched)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "gate-rerun.py"
            target.write_text(patched)
            spec = importlib.util.spec_from_file_location("patched_gate", target)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.judge("T1", {"content": None})[0], "ERROR")
            bad = {
                "stop_reason": "tool_use",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "function",
                        "input": {"path": "/tmp/test.txt", "content": "hello world"},
                    }
                ],
            }
            self.assertEqual(module.judge("T1", bad)[0], "PARTIAL")
            self.assertEqual(module.judge("T5", {"error": "offline"})[0], "ERROR")
            self.assertEqual(module.judge("T2", {"content": None})[0], "ERROR")

    def test_rejects_unexpected_source_and_cli(self):
        with self.assertRaises(ValueError):
            patch_v4_gate.apply("broken")
        source = SOURCE.read_text()
        with self.assertRaises(ValueError):
            patch_v4_gate.apply(source.replace("def judge(gate, d):", "broken"))
        with self.assertRaises(ValueError):
            patch_v4_gate.apply(
                source.replace('verdict = "clean"', 'verdict = "broken"')
            )
        with self.assertRaises(ValueError):
            patch_v4_gate.apply(
                source.replace('"thinking": {"type": "disabled"}', "broken"),
                adaptive=True,
            )
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "gate-rerun.py"
            target.write_text(source)
            with patch.object(sys, "argv", ["patch_v4_gate.py", str(target)]):
                runpy.run_module("patch_v4_gate", run_name="__main__")
            self.assertIn("import gate_score", target.read_text())


if __name__ == "__main__":
    unittest.main()
