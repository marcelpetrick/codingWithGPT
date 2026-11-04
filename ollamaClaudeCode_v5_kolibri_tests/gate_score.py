#!/usr/bin/env python3
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Strict checks for the v4 T1 and T5 tool-call gates."""


def first_call(response):
    content = response.get("content")
    if not isinstance(content, list) or not content:
        return None, ("ERROR", "empty or invalid API content")
    calls = [
        item
        for item in content
        if isinstance(item, dict) and item.get("type") == "tool_use"
    ]
    if not calls:
        return None, ("FAIL", "no tool call")
    return calls[0], None


def t1(response):
    call, problem = first_call(response)
    if problem:
        return problem
    args = call.get("input")
    if (
        response.get("stop_reason") == "tool_use"
        and call.get("name") == "write_file"
        and isinstance(args, dict)
        and args.get("path") == "/tmp/test.txt"
        and args.get("content") == "hello world"
    ):
        return "PASS", "correct tool and arguments"
    return "PARTIAL", "wrong tool, stop reason or arguments"


def t5(response):
    call, problem = first_call(response)
    if problem:
        return problem
    if call.get("name") != "apply_patch":
        return "FAIL", "wrong tool"
    if response.get("stop_reason") != "tool_use":
        return "PARTIAL", "wrong stop reason"
    args = call.get("input")
    if not isinstance(args, dict):
        return "PARTIAL", "arguments are not an object"
    if (
        args.get("commit_message") != "refactor: rename foo to bar"
        or args.get("strategy") != "squash"
    ):
        return "PARTIAL", "commit message or strategy mismatch"
    edits = args.get("edits")
    if not isinstance(edits, list) or any(not isinstance(edit, dict) for edit in edits):
        return "PARTIAL", "edits are not objects"
    if any(
        not isinstance(edit.get("path"), str) or not isinstance(edit.get("mode"), str)
        for edit in edits
    ):
        return "PARTIAL", "edit paths or modes are not strings"
    pairs = {(edit.get("path"), edit.get("mode")) for edit in edits}
    if (
        pairs != {("src/main.py", "modify"), ("src/old.py", "delete")}
        or len(edits) != 2
    ):
        return "PARTIAL", "edit paths or modes mismatch"
    modified = next(edit for edit in edits if edit.get("path") == "src/main.py")
    hunks = modified.get("hunks")
    if not isinstance(hunks, list) or not any(
        isinstance(hunk, dict)
        and isinstance(hunk.get("old"), str)
        and isinstance(hunk.get("new"), str)
        and "foo" in hunk["old"]
        and "bar" in hunk["new"]
        for hunk in hunks
    ):
        return "PARTIAL", "rename hunk missing"
    return "PASS", "correct nested arguments"
