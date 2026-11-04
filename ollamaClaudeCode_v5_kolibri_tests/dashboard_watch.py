#!/usr/bin/env python3
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Refresh the dashboard when benchmark result files are closed."""

import ctypes
import os
from pathlib import Path
import struct
import sys

import make_dashboard

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
MEASUREMENTS = ROOT / "measurements"
CLOSE_WRITE = 0x00000008
CREATE = 0x00000100
MOVED_TO = 0x00000080


def sync():
    sources = (
        (
            RESULTS / "coding" / "results" / "cc-session-sandboxed.tsv",
            "coding-current.tsv",
        ),
        (
            RESULTS / "deep" / "kolibri1" / "kolibri1_q3ks-ctx147456-nothink-ab.tsv",
            "deep-kolibri.tsv",
        ),
        (
            RESULTS / "deep" / "qwen3.6" / "qwen3.6_35b-a3b-q4_K_M-agentic.tsv",
            "deep-qwen.tsv",
        ),
        (RESULTS / "fidelity" / "results" / "gate-extra.tsv", "fidelity.tsv"),
        (
            RESULTS / "t1-adaptive" / "results" / "gate-rerun.raw.jsonl",
            "adaptive-t1.jsonl",
        ),
    )
    for source, name in sources:
        target = MEASUREMENTS / name
        if not source.exists():
            continue
        payload = source.read_bytes()
        if not payload or not payload.endswith(b"\n"):
            continue
        if name.endswith(".tsv"):
            lines = payload.splitlines()
            payload = (
                b"\n".join(
                    line + b"-" if line.endswith(b"\t") else line for line in lines
                )
                + b"\n"
            )
        if not target.exists() or target.read_bytes() != payload:
            temporary = target.with_name(target.name + ".new")
            temporary.write_bytes(payload)
            os.replace(temporary, target)
    make_dashboard.main()


def watch():
    libc = ctypes.CDLL(None, use_errno=True)
    fd = libc.inotify_init1(os.O_CLOEXEC)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "inotify_init1 failed")
    try:
        descriptors = {}
        candidates = (
            RESULTS,
            RESULTS / "coding" / "results",
            RESULTS / "deep",
            RESULTS / "deep" / "kolibri1",
            RESULTS / "deep" / "qwen3.6",
            RESULTS / "fidelity" / "results",
            RESULTS / "t1-adaptive" / "results",
        )

        def add_existing():
            for path in candidates:
                if path in descriptors.values() or not path.is_dir():
                    continue
                wd = libc.inotify_add_watch(
                    fd, os.fsencode(path), CLOSE_WRITE | CREATE | MOVED_TO
                )
                if wd < 0:
                    raise OSError(ctypes.get_errno(), f"Cannot watch {path}")
                descriptors[wd] = path

        add_existing()
        sync()
        while True:
            data = os.read(fd, 65536)
            offset = 0
            changed = False
            finished = False
            while offset < len(data):
                wd, mask, _cookie, length = struct.unpack_from("iIII", data, offset)
                offset += 16
                name = (
                    data[offset : offset + length]
                    .split(b"\0", 1)[0]
                    .decode(errors="replace")
                )
                offset += length
                if mask & (CREATE | MOVED_TO):
                    add_existing()
                if mask & CLOSE_WRITE:
                    changed = True
                    if descriptors.get(wd) == RESULTS and name == "thinking.log":
                        finished = True
            if changed:
                sync()
            if finished:
                return
    finally:
        os.close(fd)


if __name__ == "__main__":
    try:
        watch()
    except OSError as error:
        print(f"Dashboard watcher stopped: {error}", file=sys.stderr)
        sys.exit(1)
