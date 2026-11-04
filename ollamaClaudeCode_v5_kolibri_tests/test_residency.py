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


if __name__ == "__main__":
    unittest.main()
