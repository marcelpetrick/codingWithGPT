# test_main.py
import os
import tempfile
import time
import unittest
from pathlib import Path

from main import (
    ScreenshotRenamerError,
    build_rename_plan,
    find_pngs,
    rename_screenshots,
)


class ScreenshotRenamerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmpdir_obj.name)

    def tearDown(self) -> None:
        self.tmpdir_obj.cleanup()

    def _create_png(self, name: str, mtime: float) -> Path:
        path = self.tmpdir / name
        path.write_bytes(b"test")
        os.utime(path, (mtime, mtime))
        return path

    def test_find_pngs_sorted_by_mtime(self) -> None:
        base = time.time()
        f1 = self._create_png("b.png", base + 20)
        f2 = self._create_png("a.png", base)
        f3 = self._create_png("c.PNG", base + 10)

        files = find_pngs(self.tmpdir)
        self.assertEqual([f.name for f in files], [f2.name, f3.name, f1.name])

    def test_find_pngs_no_pngs_raises(self) -> None:
        (self.tmpdir / "not_png.txt").write_text("x")
        with self.assertRaises(ScreenshotRenamerError):
            find_pngs(self.tmpdir)

    def test_build_rename_plan_too_many_files(self) -> None:
        base = time.time()
        files = []
        for i in range(101):
            files.append(self._create_png(f"file{i}.png", base + i))
        with self.assertRaises(ScreenshotRenamerError):
            build_rename_plan(files)

    def test_rename_screenshots_simple_case(self) -> None:
        base = time.time()
        self._create_png("shot3.png", base + 30)
        self._create_png("shot1.png", base)
        self._create_png("shot2.png", base + 10)

        rename_screenshots(self.tmpdir)

        pngs = sorted(p.name for p in self.tmpdir.glob("*.png"))
        self.assertEqual(pngs, ["img00.png", "img01.png", "img02.png"])

    def test_rename_aborts_if_target_exists_unrelated(self) -> None:
        base = time.time()
        self._create_png("shot1.png", base)
        self._create_png("shot2.png", base + 10)
        # Existing conflicting file not in the rename set.
        (self.tmpdir / "img00.png").write_bytes(b"keep")

        with self.assertRaises(ScreenshotRenamerError):
            rename_screenshots(self.tmpdir)

        # Original files still present (no rename performed).
        self.assertTrue((self.tmpdir / "shot1.png").exists())
        self.assertTrue((self.tmpdir / "shot2.png").exists())
        self.assertTrue((self.tmpdir / "img00.png").exists())

    def test_find_pngs_invalid_directory(self) -> None:
        bogus = self.tmpdir / "does_not_exist"
        with self.assertRaises(ScreenshotRenamerError):
            find_pngs(bogus)


if __name__ == "__main__":
    unittest.main()
