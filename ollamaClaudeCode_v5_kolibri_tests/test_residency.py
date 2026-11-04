# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Safety checks for the residency probe; no server access is required."""
import unittest
from unittest.mock import patch

import residency


class ResidencyTest(unittest.TestCase):
    def test_idle_and_foreign_models(self):
        with patch.object(residency, "resident", return_value=[]):
            residency.ensure_idle()
        with patch.object(residency, "resident", return_value=[{"name": "foreign"}]):
            with self.assertRaisesRegex(RuntimeError, "busy"):
                residency.ensure_idle()
            with self.assertRaisesRegex(RuntimeError, "refusing"):
                residency.unload_ours()

    def test_only_own_model_is_unloaded(self):
        with patch.object(residency, "resident", side_effect=[[{"name": residency.MODEL}], []]), patch.object(residency, "request") as request:
            residency.unload_ours()
            request.assert_called_once_with("/api/generate", {"model": residency.MODEL, "keep_alive": 0}, timeout=60)

    def test_complete_and_spilled_runs(self):
        response = {"done": True, "response": "391", "prompt_eval_count": 12}
        for gpu in (100, 80):
            model = {"name": residency.MODEL, "size": 100, "size_vram": gpu, "context_length": 4096}
            with self.subTest(gpu=gpu), patch.object(residency, "resident", side_effect=[[], [model]]), patch.object(residency, "request", return_value=response):
                result = residency.run_one(4096, "0.40.11", "digest")
                self.assertEqual(result["full_gpu"], gpu == 100)

    def test_empty_response_is_not_a_result(self):
        with patch.object(residency, "resident", return_value=[]), patch.object(residency, "request", return_value={"done": True, "response": "", "prompt_eval_count": 1}):
            with self.assertRaisesRegex(RuntimeError, "Incomplete"):
                residency.run_one(4096, "0.40.11", "digest")

    def test_wrong_context_is_not_a_result(self):
        model = {"name": residency.MODEL, "size": 100, "size_vram": 100, "context_length": 2048}
        response = {"done": True, "response": "391", "prompt_eval_count": 12}
        with patch.object(residency, "resident", side_effect=[[], [model]]), patch.object(residency, "request", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "Requested context"):
                residency.run_one(4096, "0.40.11", "digest")

class MoreResidencyTests(unittest.TestCase):
    def test_request_decodes_json_without_proxy(self):
        from io import BytesIO
        from unittest.mock import MagicMock
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value = BytesIO(b'{"ok": true}')
        with patch.object(residency.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(residency.request("/test", {"a": 1}), {"ok": True})

    def test_resident_rejects_missing_models(self):
        with patch.object(residency, "request", return_value={}):
            with self.assertRaisesRegex(RuntimeError, "Missing resident"):
                residency.resident()
        with patch.object(residency, "request", return_value={"models": []}):
            self.assertEqual(residency.resident(), [])

    def test_unload_when_already_idle(self):
        with patch.object(residency, "resident", return_value=[]), patch.object(residency, "request") as request:
            residency.unload_ours()
            request.assert_not_called()

    def test_bad_resident_states_are_rejected(self):
        response = {"done": True, "response": "391", "prompt_eval_count": 12}
        cases = [
            ([{"name": "foreign"}], "Unexpected"),
            ([{"name": residency.MODEL, "size": 0, "size_vram": 0}], "memory accounting"),
        ]
        for models, message in cases:
            with self.subTest(message=message), patch.object(residency, "resident", side_effect=[[], models]), patch.object(residency, "request", return_value=response):
                with self.assertRaisesRegex(RuntimeError, message):
                    residency.run_one(4096, "0.40.11", "digest")

    def test_main_rejects_invalid_server_and_tags(self):
        cases = [
            ([{"version": "wrong"}], "Unexpected server"),
            ([{"version": "0.40.11"}, {}], "Missing tag list"),
            ([{"version": "0.40.11"}, {"models": []}], "Model is missing"),
        ]
        for responses, message in cases:
            with self.subTest(message=message), patch.object(residency, "request", side_effect=responses), patch.object(residency, "ensure_idle"):
                with self.assertRaisesRegex(RuntimeError, message):
                    residency.main()

    def test_main_records_results_and_stops_on_spill(self):
        import tempfile
        from pathlib import Path
        responses = [{"version": "0.40.11"}, {"models": [{"name": residency.MODEL, "digest": "abc"}]}]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "results" / "residency.jsonl"
            results = [{"context": 4096, "full_gpu": True}, {"context": 8192, "full_gpu": False}]
            with patch.object(residency, "RESULTS", output), patch.object(residency, "request", side_effect=responses), patch.object(residency, "ensure_idle"), patch.object(residency, "unload_ours") as unload, patch.object(residency, "run_one", side_effect=results):
                residency.main()
                self.assertEqual(unload.call_count, 2)
                self.assertEqual(len(output.read_text().splitlines()), 2)
            with patch.object(residency, "RESULTS", output), patch.object(residency, "request", side_effect=responses), patch.object(residency, "ensure_idle"):
                with self.assertRaisesRegex(RuntimeError, "Result file exists"):
                    residency.main()

    def test_main_propagates_probe_errors(self):
        import tempfile
        from pathlib import Path
        responses = [{"version": "0.40.11"}, {"models": [{"name": residency.MODEL, "digest": "abc"}]}]
        with tempfile.TemporaryDirectory() as tmp, patch.object(residency, "RESULTS", Path(tmp) / "results" / "residency.jsonl"), patch.object(residency, "request", side_effect=responses), patch.object(residency, "ensure_idle"), patch.object(residency, "run_one", side_effect=RuntimeError("failed")):
            with self.assertRaisesRegex(RuntimeError, "failed"):
                residency.main()

    def test_cli_stops_on_network_error(self):
        import runpy
        with patch.object(residency.urllib.request, "build_opener", side_effect=OSError("offline")):
            with self.assertRaises(SystemExit) as result:
                runpy.run_module("residency", run_name="__main__")
            self.assertEqual(result.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
