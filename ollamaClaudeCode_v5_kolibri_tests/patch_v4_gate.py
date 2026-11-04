#!/usr/bin/env python3
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Patch a copied v4 gate runner to use strict, fail-fast scoring."""

from pathlib import Path
import sys


def apply(source, adaptive=False):
    marker = "import argparse\n"
    if source.count(marker) != 1:
        raise ValueError("Unexpected v4 imports")
    source = source.replace(marker, marker + "import gate_score\n", 1)
    old = "def judge(gate, d):"
    new = '''def judge(gate, d):
    if d.get("error"):
        return "ERROR", str(d["error"])[:60]
    if gate == "T1":
        return gate_score.t1(d)
    if gate == "T5":
        return gate_score.t5(d)
    if not d.get("content"):
        return "ERROR", "empty API content"'''
    if source.count(old) != 1:
        raise ValueError("Unexpected v4 scorer")
    source = source.replace(old, new, 1)
    old = 'verdict = "clean" if n_pass == a.n else "systematic" if n_pass <= a.n // 2 else "flaky"'
    new = 'verdict = "clean" if n_pass == a.n else "systematic" if a.n >= 8 and a.n - n_pass >= 3 else "flaky" if a.n >= 8 else "preliminary"'
    if source.count(old) != 1:
        raise ValueError("Unexpected v4 summary")
    source = source.replace(old, new, 1)
    if adaptive:
        old = '"thinking": {"type": "disabled"}'
        if source.count(old) != 1:
            raise ValueError("Unexpected thinking setting")
        source = source.replace(old, '"thinking": {"type": "adaptive"}', 1)
    return source


def main():
    path = Path(sys.argv[1])
    path.write_text(apply(path.read_text(), adaptive="--adaptive" in sys.argv[2:]))


if __name__ == "__main__":
    main()
