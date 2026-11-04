# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that the pull stops before writing when the tag list is unreadable."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class PullTest(unittest.TestCase):
    def test_tag_read_failure_does_not_start_pull(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(Path(__file__).with_name("pull-model.sh"), root)
            fakebin = root / "bin"
            fakebin.mkdir()
            curl = fakebin / "curl"
            curl.write_text('''#!/usr/bin/env bash
case "$*" in
  */api/version*) printf '{"version":"0.40.11"}' ;;
  */api/ps*) printf '{"models":[]}' ;;
  */api/tags*) exit 22 ;;
  */api/pull*) touch "$PULL_CALLED" ;;
esac
''')
            curl.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{fakebin}:{env['PATH']}"
            env["PULL_CALLED"] = str(root / "pull-called")
            result = subprocess.run(["bash", str(root / "pull-model.sh")], env=env, capture_output=True, timeout=10, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / "pull-called").exists())


if __name__ == "__main__":
    unittest.main()
