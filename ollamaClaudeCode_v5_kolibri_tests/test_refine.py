# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the maximum-context search."""
import unittest
import refine


class ContextSearchTest(unittest.TestCase):
    def test_refines_until_1024_apart(self):
        rows = [{"context": 4096, "full_gpu": True}, {"context": 8192, "full_gpu": False}]
        self.assertEqual(refine.next_context(rows), 6144)
        rows.append({"context": 6144, "full_gpu": True})
        self.assertEqual(refine.next_context(rows), 7168)
        rows.append({"context": 7168, "full_gpu": False})
        self.assertIsNone(refine.next_context(rows))

    def test_below_first_rung(self):
        rows = [{"context": 4096, "full_gpu": False}]
        self.assertEqual(refine.next_context(rows), 2048)
        rows.append({"context": 2048, "full_gpu": True})
        self.assertEqual(refine.next_context(rows), 3072)
        rows[-1]["full_gpu"] = False
        self.assertIsNone(refine.next_context(rows))

    def test_no_spill(self):
        self.assertIsNone(refine.next_context([{"context": 4096, "full_gpu": True}]))


if __name__ == "__main__":
    unittest.main()
