# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check strict tool names, types and nested argument fidelity."""

import copy
import unittest

import gate_score


def response(name, args):
    return {
        "stop_reason": "tool_use",
        "content": [{"type": "tool_use", "name": name, "input": args}],
    }


class GateScoreTest(unittest.TestCase):
    def test_empty_and_no_call(self):
        self.assertEqual(gate_score.t1({"content": None})[0], "ERROR")
        self.assertEqual(gate_score.t5({"content": []})[0], "ERROR")
        self.assertEqual(gate_score.t1({"content": [{"type": "text"}]})[0], "FAIL")

    def test_t1_requires_tool_and_string_content(self):
        good = response(
            "write_file", {"path": "/tmp/test.txt", "content": "hello world"}
        )
        self.assertEqual(gate_score.t1(good)[0], "PASS")
        for bad in (
            response("function", good["content"][0]["input"]),
            response(
                "write_file", {"path": "/tmp/test.txt", "content": {"type": "string"}}
            ),
            response("write_file", None),
            dict(good, stop_reason="end_turn"),
        ):
            self.assertEqual(gate_score.t1(bad)[0], "PARTIAL")

    def test_t5_requires_exact_nested_fields(self):
        args = {
            "commit_message": "refactor: rename foo to bar",
            "strategy": "squash",
            "edits": [
                {
                    "path": "src/main.py",
                    "mode": "modify",
                    "hunks": [{"old": "foo", "new": "bar"}],
                },
                {"path": "src/old.py", "mode": "delete"},
            ],
        }
        good = response("apply_patch", args)
        self.assertEqual(gate_score.t5(good)[0], "PASS")
        self.assertEqual(gate_score.t5(response("other", args))[0], "FAIL")
        self.assertEqual(
            gate_score.t5(dict(good, stop_reason="end_turn"))[0], "PARTIAL"
        )
        self.assertEqual(gate_score.t5(response("apply_patch", None))[0], "PARTIAL")
        for key, value in (
            ("commit_message", {"type": "string"}),
            ("strategy", "merge"),
            ("edits", None),
            ("edits", ["bad"]),
            ("edits", []),
        ):
            bad = copy.deepcopy(args)
            bad[key] = value
            self.assertEqual(gate_score.t5(response("apply_patch", bad))[0], "PARTIAL")
        bad_path = copy.deepcopy(args)
        bad_path["edits"][0]["path"] = {"type": "string"}
        self.assertEqual(gate_score.t5(response("apply_patch", bad_path))[0], "PARTIAL")
        bad = copy.deepcopy(args)
        bad["edits"][0]["hunks"] = [{"old": "foo", "new": "wrong"}]
        self.assertEqual(gate_score.t5(response("apply_patch", bad))[0], "PARTIAL")


if __name__ == "__main__":
    unittest.main()
