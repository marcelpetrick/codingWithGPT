# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise live dashboard updates using real filesystem events."""

import os
from pathlib import Path
import runpy
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

import dashboard_watch as watcher


class DashboardWatchTest(unittest.TestCase):
    def test_copies_only_complete_result_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results"
            measurements = root / "measurements"
            source = results / "coding" / "results" / "cc-session-sandboxed.tsv"
            source.parent.mkdir(parents=True)
            measurements.mkdir()
            with (
                patch.object(watcher, "RESULTS", results),
                patch.object(watcher, "MEASUREMENTS", measurements),
                patch.object(watcher.make_dashboard, "main") as build,
            ):
                watcher.sync()
                source.write_bytes(b"date\tollama\tmodel\nfirst")
                watcher.sync()
                self.assertFalse((measurements / "coding-current.tsv").exists())
                source.write_bytes(b"date\tollama\tmodel\nfirst\n")
                watcher.sync()
                self.assertEqual(
                    (measurements / "coding-current.tsv").read_bytes(),
                    source.read_bytes(),
                )
                watcher.sync()
                source.write_bytes(
                    b"date\tollama\tmodel\tnote\nfirst\tversion\tname\t\n"
                )
                watcher.sync()
                self.assertTrue(
                    (measurements / "coding-current.tsv")
                    .read_bytes()
                    .endswith(b"name\t-\n")
                )
                self.assertEqual(build.call_count, 5)

    def test_real_file_events_refresh_then_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "results"
            measurements = root / "measurements"
            source = results / "coding" / "results" / "cc-session-sandboxed.tsv"
            source.parent.mkdir(parents=True)
            measurements.mkdir()
            ready = threading.Event()
            updated = threading.Event()

            def build():
                if ready.is_set():
                    updated.set()
                ready.set()

            with (
                patch.object(watcher, "RESULTS", results),
                patch.object(watcher, "MEASUREMENTS", measurements),
                patch.object(watcher.make_dashboard, "main", side_effect=build),
            ):
                thread = threading.Thread(target=watcher.watch, daemon=True)
                thread.start()
                self.assertTrue(ready.wait(5))
                source.write_text("date\tollama\tmodel\nfirst\n")
                self.assertTrue(updated.wait(5))
                (results / "thinking.log").write_text("finished\n")
                thread.join(5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(
                    (measurements / "coding-current.tsv").read_text(),
                    source.read_text(),
                )

    def test_init_failure_is_reported(self):
        fake = MagicMock()
        fake.inotify_init1.return_value = -1
        with patch.object(watcher.ctypes, "CDLL", return_value=fake):
            with self.assertRaises(OSError):
                watcher.watch()
            with self.assertRaises(SystemExit) as result:
                runpy.run_module("dashboard_watch", run_name="__main__")
            self.assertEqual(result.exception.code, 1)

    def test_watch_registration_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.mkdir(exist_ok=True)
            readfd, writefd = os.pipe()
            fake = MagicMock()
            fake.inotify_init1.return_value = readfd
            fake.inotify_add_watch.return_value = -1
            try:
                with (
                    patch.object(watcher, "RESULTS", root),
                    patch.object(watcher.ctypes, "CDLL", return_value=fake),
                ):
                    with self.assertRaises(OSError):
                        watcher.watch()
            finally:
                os.close(writefd)


if __name__ == "__main__":
    unittest.main()
