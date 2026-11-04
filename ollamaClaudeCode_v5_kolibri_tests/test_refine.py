# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the maximum-context search."""
import json
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import refine


class ContextSearchTest(unittest.TestCase):
    def test_refines_until_1024_apart(self):
        rows = [{"context": 4096, "full_gpu": True}, {"context": 8192, "full_gpu": False}]
        self.assertEqual(refine.next_context(rows), 6144)
        rows.append({"context": 6144, "full_gpu": True})
        self.assertEqual(refine.next_context(rows), 7168)
        rows.append({"context": 7168, "full_gpu": False})
        self.assertIsNone(refine.next_context(rows))

    def test_below_first_rung(self):
        rows = [{"context": 4096, "full_gpu": False}]
        self.assertEqual(refine.next_context(rows), 2048)
        rows.append({"context": 2048, "full_gpu": True})
        self.assertEqual(refine.next_context(rows), 3072)
        rows[-1]["full_gpu"] = False
        self.assertIsNone(refine.next_context(rows))

    def test_no_spill(self):
        self.assertIsNone(refine.next_context([{"context": 4096, "full_gpu": True}]))


class RefinementRunTest(unittest.TestCase):
    def row(self, ctx, full=True):
        return {"context": ctx, "full_gpu": full, "digest": "abc", "ollama": "0.40.11"}

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(refine.read_rows(Path(tmp) / "absent"), [])

    def test_main_refines_and_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ladder = Path(tmp) / "ladder.jsonl"
            results = Path(tmp) / "refinement.jsonl"
            ladder.write_text("\n".join(json.dumps(r) for r in [self.row(4096), self.row(8192, False)]) + "\n")
            tags = {"models": [{"name": refine.residency.MODEL, "digest": "abc"}]}
            api = lambda *_args: {"version": "0.40.11"} if _args[0] == "/api/version" else tags
            with patch.object(refine.residency, "RESULTS", ladder), patch.object(refine, "RESULTS", results), patch.object(refine.residency, "request", side_effect=api), patch.object(refine.residency, "ensure_idle"), patch.object(refine.residency, "unload_ours") as unload, patch.object(refine.residency, "run_one", side_effect=lambda ctx, *_: self.row(ctx, ctx == 6144)):
                refine.main()
                self.assertEqual(unload.call_count, 2)
                self.assertEqual([r["context"] for r in refine.read_rows(results)], [6144, 7168])
                refine.main()
                self.assertEqual(unload.call_count, 2)
                results.write_text(json.dumps(self.row(5120)) + "\n")
                with self.assertRaisesRegex(RuntimeError, "refinement results"):
                    refine.main()

    def test_invalid_ladders_and_ceiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            ladder = Path(tmp) / "ladder.jsonl"
            tags = {"models": [{"name": refine.residency.MODEL, "digest": "abc"}]}
            api = lambda path: {"version": "0.40.11"} if path == "/api/version" else tags
            with patch.object(refine.residency, "RESULTS", ladder), patch.object(refine.residency, "request", side_effect=api), patch.object(refine.residency, "ensure_idle"):
                with self.assertRaisesRegex(RuntimeError, "no results"):
                    refine.main()
                ladder.write_text(json.dumps(self.row(123)) + "\n")
                with self.assertRaisesRegex(RuntimeError, "inconsistent"):
                    refine.main()
                ladder.write_text(json.dumps(self.row(4096)) + "\n")
                with self.assertRaisesRegex(RuntimeError, "did not finish"):
                    refine.main()
                ladder.write_text("\n".join(json.dumps(self.row(ctx)) for ctx in refine.residency.CONTEXTS) + "\n")
                refine.main()

    def test_invalid_version_and_tags(self):
        cases = [([{"version": "bad"}], "version changed"), ([{"version": "0.40.11"}, {}], "Missing tag"), ([{"version": "0.40.11"}, {"models": []}], "digest missing")]
        for responses, message in cases:
            with self.subTest(message=message), patch.object(refine.residency, "request", side_effect=responses), patch.object(refine.residency, "ensure_idle"):
                with self.assertRaisesRegex(RuntimeError, message):
                    refine.main()

    def test_cli_error(self):
        with patch.object(refine.residency, "request", side_effect=OSError("offline")):
            with self.assertRaises(SystemExit) as result:
                runpy.run_module("refine", run_name="__main__")
            self.assertEqual(result.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
