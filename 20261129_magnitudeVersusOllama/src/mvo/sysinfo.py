# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Facts recorded with every result row: GPU, driver, VRAM in use, git commit."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence

Runner = Callable[[Sequence[str]], str]


def run_text(cmd: Sequence[str]) -> str:
    """Run a command and return its stdout, or an empty string if it fails."""
    try:
        result = subprocess.run(list(cmd), capture_output=True, text=True, timeout=30, check=False)
    except OSError, subprocess.TimeoutExpired:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def gpu_facts(run: Runner = run_text) -> dict[str, str | int]:
    """Return GPU name, driver and VRAM used/total in MiB (empty values without nvidia-smi)."""
    out = run(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ]
    )
    if not out:
        return {"gpu": "", "driver": "", "vram_used_mib": -1, "vram_total_mib": -1}
    name, driver, used, total = (part.strip() for part in out.splitlines()[0].split(","))
    return {"gpu": name, "driver": driver, "vram_used_mib": int(used), "vram_total_mib": int(total)}


def git_commit(run: Runner = run_text) -> str:
    """Return the short commit of this project, with '+dirty' if the tree has changes."""
    commit = run(["git", "rev-parse", "--short", "HEAD"])
    dirty = run(["git", "status", "--porcelain", "--", "src", "data"])
    return commit + ("+dirty" if dirty else "")
