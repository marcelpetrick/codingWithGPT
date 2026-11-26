# SPDX-License-Identifier: GPL-3.0-or-later
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import build_release


class ReleaseArchiveTest(unittest.TestCase):
    def test_archive_excludes_untracked_documentation_and_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.git(root, "init", "--quiet")
            files = (
                "traffic_light.py",
                "agent_status.py",
                "requirements-monitor.txt",
                "README.md",
                "LICENSE",
                "docs/example.md",
                "udev/example.rules",
            )
            for name in files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("websockets==17.4\n", encoding="utf-8")
            self.git(root, "add", *files)
            self.git(
                root,
                "-c",
                "user.name=Release fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "test(usb): prepare release fixture",
            )
            (root / "docs" / "local-note.md").touch()
            (root / "udev" / "local-only.rules").touch()

            with patch.object(build_release, "ROOT", root):
                archive = build_release.build_release("v1.0.0", root / "dist")
            with tarfile.open(archive) as bundle:
                packaged = {
                    member.name.split("/", 1)[1]
                    for member in bundle.getmembers()
                    if member.isfile()
                }
            self.assertEqual(packaged, set(files))

    @staticmethod
    def git(root, *args):
        subprocess.run(["git", *args], cwd=root, check=True)
