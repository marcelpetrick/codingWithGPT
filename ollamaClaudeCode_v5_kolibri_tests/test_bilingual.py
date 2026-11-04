# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test bilingual scoring and server safety checks."""

import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

import bilingual


class BilingualTest(unittest.TestCase):
    def test_exact_answer(self):
        self.assertTrue(bilingual.score(" 391.\n", "391"))
        self.assertFalse(bilingual.score("1391", "391"))
        self.assertFalse(bilingual.score("The answer is 391", "391"))

    def test_residency_checks(self):
        model = bilingual.MODELS[0]
        good = {"name": model, "size": 10, "size_vram": 10, "context_length": 147456}
        cases = [
            ([], "Unexpected resident"),
            ([dict(good, name="other")], "Unexpected resident"),
            ([dict(good, size=None)], "memory accounting"),
            ([dict(good, size=0)], "GPU spill"),
            ([dict(good, size_vram=9)], "GPU spill"),
            ([dict(good, context_length=2048)], "Unexpected context"),
        ]
        for value, message in cases:
            with (
                self.subTest(message=message),
                patch.object(bilingual.residency, "resident", return_value=value),
            ):
                with self.assertRaisesRegex(RuntimeError, message):
                    bilingual.check_resident(model)
        with patch.object(bilingual.residency, "resident", return_value=[good]):
            bilingual.check_resident(model)
        control = dict(good, name=bilingual.MODELS[1], context_length=262144)
        with patch.object(bilingual.residency, "resident", return_value=[control]):
            bilingual.check_resident(bilingual.MODELS[1])

    def test_main_records_and_resumes(self):
        model = bilingual.MODELS[0]
        tasks = (("en", "English", "question", "391"), ("de", "German", "frage", "391"))
        calls = []

        def request(path, data=None, timeout=30):
            calls.append(path)
            if path == "/api/version":
                return {"version": "0.40.11"}
            if path == "/api/tags":
                return {"models": [{"name": model, "digest": "abc"}]}
            if path == "/api/chat":
                return {
                    "done": True,
                    "message": {"content": "391"},
                    "prompt_eval_count": 3,
                }
            return {}

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "results" / "results.jsonl"
            with (
                patch.object(bilingual, "RESULTS", output),
                patch.object(bilingual, "MODELS", (model,)),
                patch.object(bilingual, "TASKS", tasks),
                patch.object(bilingual.residency, "request", side_effect=request),
                patch.object(bilingual.residency, "ensure_idle"),
                patch.object(bilingual, "check_resident"),
            ):
                bilingual.main()
                rows = [json.loads(line) for line in output.read_text().splitlines()]
                self.assertEqual([r["pass"] for r in rows], [True, True])
                bilingual.main()
                self.assertEqual(calls.count("/api/chat"), 2)
                output.write_text(
                    output.read_text() + output.read_text().splitlines()[0] + "\n"
                )
                with self.assertRaisesRegex(RuntimeError, "Inconsistent"):
                    bilingual.main()

    def test_invalid_preflight_and_response(self):
        model = bilingual.MODELS[0]
        cases = [
            ([{"version": "bad"}], "version changed"),
            ([{"version": "0.40.11"}, {}], "Missing tag list"),
            ([{"version": "0.40.11"}, {"models": []}], "digest missing"),
        ]
        for responses, message in cases:
            with (
                self.subTest(message=message),
                patch.object(bilingual.residency, "request", side_effect=responses),
            ):
                with self.assertRaisesRegex(RuntimeError, message):
                    bilingual.main()
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(bilingual, "RESULTS", Path(tmp) / "r.jsonl"),
            patch.object(bilingual, "MODELS", (model,)),
            patch.object(bilingual, "TASKS", (("en", "English", "question", "391"),)),
            patch.object(
                bilingual.residency,
                "request",
                side_effect=[
                    {"version": "0.40.11"},
                    {"models": [{"name": model, "digest": "abc"}]},
                    {"done": True, "message": {"content": ""}, "prompt_eval_count": 1},
                ],
            ),
            patch.object(bilingual.residency, "ensure_idle"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Incomplete"):
                bilingual.main()

    def test_cli_error(self):
        with patch.object(
            bilingual.residency, "request", side_effect=OSError("offline")
        ):
            with self.assertRaises(SystemExit) as result:
                runpy.run_module("bilingual", run_name="__main__")
            self.assertEqual(result.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
