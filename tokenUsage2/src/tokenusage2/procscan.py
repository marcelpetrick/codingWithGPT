# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Running agent processes, read from ``/proc``.

Shell functions and aliases are expanded before a CLI starts, so their names
are gone — but a profile-selecting ``CODEX_HOME`` or ``CLAUDE_CONFIG_DIR``
survives in the process environment. Reading it finds homes that no rc file
mentions and tells which accounts are running right now.

Only the values of the few variables in ``WANTED`` are extracted; the rest of
a process environment (which holds API keys) is never retained.
"""

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from tokenusage2.config import expand
from tokenusage2.model import Account, Tool

WANTED = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL")
HOME_VARIABLE = {Tool.CLAUDE: "CLAUDE_CONFIG_DIR", Tool.CODEX: "CODEX_HOME"}
DEFAULT_HOME = {Tool.CLAUDE: ".claude", Tool.CODEX: ".codex"}
_COMMS = {"claude": Tool.CLAUDE, "codex": Tool.CODEX, "opencode": Tool.OPENCODE}


@dataclass(frozen=True, slots=True)
class AgentProcess:
    pid: int
    tool: Tool
    env: Mapping[str, str] = field(default_factory=dict)
    model: str | None = None
    cwd: str = ""


def classify(comm: str, argv: Sequence[str]) -> Tool | None:
    """The agent a process is, by its kernel ``comm`` name.

    Native Claude Code and Codex binaries are named ``claude`` and ``codex``;
    Codex's node launcher and helper processes (``codex-code-mode``) are not
    counted, so one session is one process. npm-installed Claude Code runs as
    ``node …/@anthropic-ai/claude-code/cli.js``.
    """
    if comm in _COMMS:
        return _COMMS[comm]
    if comm in {"node", "bun"} and any("@anthropic-ai/claude-code" in arg for arg in argv[1:3]):
        return Tool.CLAUDE
    return None


def model_flag(argv: Sequence[str]) -> str | None:
    for index, arg in enumerate(argv):
        if arg == "--model" and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith("--model="):
            return arg.split("=", 1)[1]
    return None


def environ_values(raw: bytes, keys: Sequence[str] = WANTED) -> dict[str, str]:
    values = {}
    for entry in raw.split(b"\0"):
        name, sep, value = entry.partition(b"=")
        if sep and name.decode(errors="replace") in keys:
            values[name.decode()] = value.decode(errors="replace")
    return values


def scan_processes(proc: Path = Path("/proc")) -> list[AgentProcess]:
    found = []
    try:
        entries = list(os.scandir(proc))
    except OSError:
        return []
    for entry in entries:
        if not entry.name.isdigit():
            continue
        base = Path(entry.path)
        try:
            comm = (base / "comm").read_text(encoding="utf-8", errors="replace").strip()
            argv = [
                part.decode(errors="replace")
                for part in (base / "cmdline").read_bytes().split(b"\0")
                if part
            ]
        except OSError:
            continue
        tool = classify(comm, argv)
        if tool is None:
            continue
        try:
            env = environ_values((base / "environ").read_bytes())
        except OSError:
            env = {}
        try:
            cwd = str((base / "cwd").readlink())
        except OSError:
            cwd = ""
        found.append(
            AgentProcess(
                int(entry.name), tool, env, model_flag(argv) or env.get("ANTHROPIC_MODEL"), cwd
            )
        )
    return sorted(found, key=lambda process: process.pid)


def process_home(process: AgentProcess, home: Path, env: Mapping[str, str]) -> Path | None:
    variable = HOME_VARIABLE.get(process.tool)
    if variable is None:
        return None
    raw = process.env.get(variable)
    return expand(raw, home, env) if raw else home / DEFAULT_HOME[process.tool]


def running_by_account(
    processes: Sequence[AgentProcess],
    accounts: Sequence[Account],
    home: Path,
    env: Mapping[str, str],
) -> dict[str, int]:
    homes = {(account.tool, account.home.resolve()): account.id for account in accounts}
    opencode = [account.id for account in accounts if account.tool is Tool.OPENCODE]
    counts: dict[str, int] = {}
    for process in processes:
        if process.tool is Tool.OPENCODE:
            target = opencode[0] if opencode else None
        else:
            path = process_home(process, home, env)
            target = homes.get((process.tool, path.resolve())) if path else None
        if target is not None:
            counts[target] = counts.get(target, 0) + 1
    return counts
