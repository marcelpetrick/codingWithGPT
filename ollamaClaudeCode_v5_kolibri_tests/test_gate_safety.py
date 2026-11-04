# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that copied v4 gate scorers stop on empty API content."""

import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
V4 = ROOT.parent / "ollamaClaudeCode_v4_tielCoder"


def patch_copy(wrapper, filename, marker, target):
    source = (ROOT / wrapper).read_text()
    code = source.split(marker, 1)[1].split("\nPY\n", 1)[0]
    shutil.copy(V4 / filename, target)
    subprocess.run([sys.executable, "-c", code, str(target)], check=True)


def load(path):
    spec = importlib.util.spec_from_file_location("temporary_gate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GateSafetyTest(unittest.TestCase):
    def test_t1_scorers_reject_null_content(self):
        for wrapper in ("gate-reliability.sh", "thinking-retry.sh"):
            with self.subTest(wrapper=wrapper), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "gate-rerun.py"
                patch_copy(
                    wrapper,
                    "gate-rerun.py",
                    "python3 - \"$out/gate-rerun.py\" <<'PY'\n",
                    target,
                )
                module = load(target)
                self.assertEqual(module.judge("T1", {"content": None})[0], "ERROR")
                self.assertEqual(module.judge("T1", {"content": []})[0], "ERROR")

    def test_fidelity_records_then_rejects_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "results").mkdir()
            target = root / "gate-extra.py"
            patch_copy(
                "fidelity-retry.sh",
                "gate-extra.py",
                "python3 - \"$out/gate-extra.py\" <<'PY'\n",
                target,
            )
            module = load(target)
            response = io.BytesIO(b'{"content": null}')
            with patch.object(module.urllib.request, "urlopen", return_value=response):
                result = module.post("http://example.invalid", "/v1/messages", {})
            self.assertEqual(result["error"], "empty API content")
            saved = json.loads((root / "results" / "api.raw.jsonl").read_text())
            self.assertIsNone(saved["response"]["content"])

    def test_deep_probe_has_no_eval_and_checks_empty_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "agentic-test.sh"
            patch_copy(
                "deep-probe.sh",
                "agentic-test.sh",
                "python3 - \"$out/agentic-test.sh\" <<'PY'\n",
                target,
            )
            subprocess.run(["bash", "-n", str(target)], check=True)
            text = target.read_text()
            self.assertNotIn('eval "$(', text)
            self.assertIn("API error or empty content", text)


if __name__ == "__main__":
    unittest.main()
