# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that the dashboard renders the recorded data safely."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import make_dashboard as dashboard


class DashboardTest(unittest.TestCase):
    def test_escape_and_model_labels(self):
        self.assertEqual(dashboard.esc('<script>"'), "&lt;script&gt;&quot;")
        self.assertEqual(dashboard.model_name("unknown:model"), "unknown:model")
        self.assertIn("data-tip=", dashboard.model_cell("unknown:<model>"))
        self.assertNotIn("<model>", dashboard.model_cell("unknown:<model>"))
        self.assertIn('data-v="7"', dashboard.text_cell("seven", 7))
        self.assertIn("1,000", dashboard.optional_number({"n": "1000"}, "n"))
        self.assertIn("—", dashboard.optional_number({}, "n"))

    def test_generated_report_uses_results_and_rescore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(dashboard, "ROOT", root):
                dashboard.main()
            page = (root / "dashboard.html").read_text()
            self.assertIn("147,456", page)
            self.assertIn("131,506", page)
            self.assertIn("PASS *", page)
            self.assertIn("KAT-Coder V2.5", page)
            self.assertIn("data-v=", page)
            self.assertIn("0.33.3", page)
            self.assertIn("0.40.11", page)
            self.assertIn("Targeted · temperature 0", page)
            self.assertIn("2/3", page)

    def test_no_current_coding_file_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = dashboard.MEASUREMENTS
            for path in source.iterdir():
                if path.name != "coding-current.tsv" and path.is_file():
                    (root / path.name).write_bytes(path.read_bytes())
            with (
                patch.object(dashboard, "ROOT", root),
                patch.object(dashboard, "MEASUREMENTS", root),
            ):
                dashboard.main()
            self.assertIn(
                "Current coding sessions", (root / "dashboard.html").read_text()
            )

    def test_empty_gate_responses_are_not_scored(self):
        rows = [
            {
                "verdict": "PASS",
                "response": {
                    "stop_reason": "tool_use",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "write_file",
                            "input": {
                                "path": "/tmp/test.txt",
                                "content": "hello world",
                            },
                        }
                    ],
                },
            },
            {"verdict": "PARTIAL", "response": {"content": [{"type": "tool_use"}]}},
            {"verdict": "FAIL", "response": {"content": None}},
        ]
        self.assertEqual(dashboard.gate_counts(rows), (1, 2, 1))

    def test_computes_medians_and_rescore_match(self):
        speed = [
            dict(
                model="kolibri1:test",
                prompt_words="2000",
                gen_tps=str(v),
                prefill_tps="12",
            )
            for v in (1, 8, 3)
        ]
        page = dashboard.speed_table(speed)
        self.assertIn("3.00", page)
        self.assertIn("1.00–8.00", page)
        row = dict(
            model="kolibri1:test",
            fixture="easy",
            run="1",
            verdict="CHEAT",
            hidden="-",
            wall_s="8",
        )
        fix = dict(
            model="kolibri1:test",
            fixture="easy",
            run="1",
            recorded_verdict="CHEAT",
            corrected_verdict="PASS",
        )
        self.assertIn("PASS *", dashboard.coding_table([row], [fix]))
        fix["run"] = "2"
        self.assertIn("CHEAT", dashboard.coding_table([row], [fix]))

    def test_additional_results_appear(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path in dashboard.MEASUREMENTS.iterdir():
                if path.is_file():
                    (root / path.name).write_bytes(path.read_bytes())
            (root / "fidelity.tsv").write_text((root / "agentic-extra.tsv").read_text())
            (root / "strict-t5.jsonl").write_text(
                (root / "nothink-t1-eight.jsonl").read_text()
            )
            (root / "parser-arm-t1.jsonl").write_text(
                (root / "nothink-t1-eight.jsonl").read_text()
            )
            (root / "reason-effort-t1.jsonl").write_text(
                (root / "nothink-t1-eight.jsonl").read_text()
            )
            (root / "adaptive-t1.jsonl").write_text(
                (root / "nothink-t1-eight.jsonl").read_text()
            )
            (root / "bilingual.jsonl").write_text(
                '{"model":"kolibri1:test","language":"German","pass":true}\n'
            )
            (root / "deep-kolibri.tsv").write_text(
                "test\tresult\tdetail\nT3_multiturn\tPASS\tused_tool_result\nT7_tool_at_long_ctx\tPASS\t3/3_at_50000_tokens\n"
            )
            with (
                patch.object(dashboard, "ROOT", root),
                patch.object(dashboard, "MEASUREMENTS", root),
            ):
                dashboard.main()
            page = (root / "dashboard.html").read_text()
            self.assertIn("English and German smoke checks", page)
            self.assertIn("Strict rerun", page)
            self.assertIn("Qwen3 parser", page)
            self.assertIn("Reasoning instruction", page)
            self.assertIn("Adaptive thinking", page)
            self.assertIn("T3 · multiturn", page)
            self.assertIn("T7 · tool_at_long_ctx", page)

    def test_jsonl_and_tsv_readers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").write_text('{"value": 1}\n')
            (root / "b").write_text("key\tvalue\nx\ty\n")
            self.assertEqual(dashboard.read_jsonl(root / "a"), [dict(value=1)])
            self.assertEqual(dashboard.read_tsv(root / "b"), [dict(key="x", value="y")])


if __name__ == "__main__":
    unittest.main()
