# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check multi-turn gates, context validation and safe resume."""

import io
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import targeted_gate as target


def call(name="read_file", args=None):
    return {
        "type": "tool_use",
        "id": "one",
        "name": name,
        "input": args if args is not None else {"path": "/app/version.txt"},
    }


class TargetedTest(unittest.TestCase):
    def test_tool_definitions_and_post(self):
        self.assertTrue(target.tool_definitions())
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value = io.BytesIO(b'{"content": []}')
        with patch.object(target.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(target.post("m", [], []), {"content": []})
        opener.open.return_value.__enter__.return_value = io.BytesIO(
            b'{"error": "bad"}'
        )
        with patch.object(target.urllib.request, "build_opener", return_value=opener):
            with self.assertRaisesRegex(RuntimeError, "Invalid API"):
                target.post("m", [], [])

    def test_t3_valid_and_invalid(self):
        cases = [
            ([{"content": None}], "INVALID"),
            ([{"content": [{"type": "text"}]}], "FAIL"),
            ([{"content": [call("wrong")]}], "FAIL"),
            ([{"content": [call(args=["bad"])]}], "FAIL"),
            (
                [{"content": [call()], "stop_reason": "tool_use"}, {"content": None}],
                "INVALID",
            ),
            (
                [
                    {"content": [call()], "stop_reason": "tool_use"},
                    {"content": [{"type": "text", "text": "4.2.1-rc3"}]},
                ],
                "PASS",
            ),
            (
                [
                    {"content": [call()], "stop_reason": "tool_use"},
                    {"content": [{"type": "text", "text": "unknown"}]},
                ],
                "FAIL",
            ),
        ]
        for responses, expected in cases:
            with (
                self.subTest(expected=expected),
                patch.object(target, "post", side_effect=responses),
            ):
                self.assertEqual(target.t3("m", [])[0], expected)

    def test_t7_valid_and_invalid(self):
        valid = {
            "content": [
                call("write_file", {"path": "/tmp/final.txt", "content": "done"})
            ],
            "usage": {"input_tokens": 40000},
            "stop_reason": "tool_use",
        }
        for value, expected in [
            (valid, "PASS"),
            (dict(valid, content=None), "INVALID"),
            (dict(valid, usage={"input_tokens": 1}), "INVALID"),
            (dict(valid, usage={"input_tokens": "bad"}), "INVALID"),
            (dict(valid, usage=[]), "INVALID"),
            (dict(valid, stop_reason="end_turn"), "FAIL"),
            (dict(valid, content=[call("wrong")]), "FAIL"),
        ]:
            with (
                self.subTest(expected=expected),
                patch.object(target, "post", return_value=value),
            ):
                self.assertEqual(target.t7("m", [])[0], expected)

    def test_resident_guards(self):
        good = {"name": "m", "size": 10, "size_vram": 10}
        for models, message in [
            ([], "Unexpected resident"),
            ([dict(good, name="other")], "Unexpected resident"),
            ([dict(good, size=None)], "memory accounting"),
            ([dict(good, size=0)], "GPU spill"),
            ([dict(good, size_vram=9)], "GPU spill"),
        ]:
            with (
                self.subTest(message=message),
                patch.object(target.residency, "resident", return_value=models),
            ):
                with self.assertRaisesRegex(RuntimeError, message):
                    target.check_resident("m")
        with patch.object(target.residency, "resident", return_value=[good]):
            target.check_resident("m")

    def test_main_records_resumes_and_rejects_invalid(self):
        model = target.MODELS[0]

        def request(path, data=None, timeout=30):
            if path == "/api/version":
                return {"version": "0.40.11"}
            if path == "/api/tags":
                return {"models": [{"name": model, "digest": "abc"}]}
            return {}

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "results.jsonl"
            with (
                patch.object(target, "RESULTS", output),
                patch.object(target, "MODELS", (model,)),
                patch.object(target.residency, "request", side_effect=request),
                patch.object(target.residency, "ensure_idle"),
                patch.object(target, "check_resident"),
                patch.object(target, "tool_definitions", return_value=[]),
                patch.object(target, "t3", return_value=("PASS", "ok", [{}])) as t3,
                patch.object(target, "t7", return_value=("FAIL", "bad", [{}])) as t7,
            ):
                target.main()
                self.assertEqual(len(output.read_text().splitlines()), 6)
                target.main()
                self.assertEqual(t3.call_count, 3)
                self.assertEqual(t7.call_count, 3)
                output.write_text(
                    output.read_text() + output.read_text().splitlines()[0] + "\n"
                )
                with self.assertRaisesRegex(RuntimeError, "Existing results"):
                    target.main()
                output.unlink()
                t3.return_value = ("INVALID", "empty", [{}])
                with self.assertRaisesRegex(RuntimeError, "Invalid gate"):
                    target.main()
                with self.assertRaisesRegex(RuntimeError, "Existing results"):
                    target.main()

    def test_preflight_and_cli_errors(self):
        for responses, message in [
            ([{"version": "bad"}], "version changed"),
            ([{"version": "0.40.11"}, {}], "Missing tag"),
            ([{"version": "0.40.11"}, {"models": []}], "digest missing"),
        ]:
            with patch.object(target.residency, "request", side_effect=responses):
                with self.assertRaisesRegex(RuntimeError, message):
                    target.main()
        with patch.object(target.residency, "request", side_effect=OSError("offline")):
            with self.assertRaises(SystemExit) as result:
                runpy.run_module("targeted_gate", run_name="__main__")
            self.assertEqual(result.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
