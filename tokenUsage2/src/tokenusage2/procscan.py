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


#: Subcommands that start a server or a one-shot utility, not an agent session.
HELPER_SUBCOMMANDS = {
    Tool.CODEX: frozenset(
        {
            "app-server",
            "mcp-server",
            "mcp",
            "login",
            "logout",
            "completion",
            "debug",
            "sandbox",
            "apply",
            "proto",
        }
    ),
    Tool.CLAUDE: frozenset(
        {
            "mcp",
            "config",
            "doctor",
            "update",
            "install",
            "migrate-installer",
            "setup-token",
            "plugin",
        }
    ),
}
#: Options that take a separate value, so the value is not taken for a subcommand.
VALUE_FLAGS = frozenset(
    {
        "-c",
        "--config",
        "-m",
        "--model",
        "-p",
        "--profile",
        "-C",
        "--cd",
        "-s",
        "--sandbox",
        "-a",
        "--ask-for-approval",
        "-i",
        "--image",
        "--add-dir",
        "--settings",
        "--permission-mode",
        "--mcp-config",
        "--fallback-model",
        "--session-id",
        "-r",
        "--resume",
    }
)


def subcommand(args: Sequence[str]) -> str | None:
    """The first positional argument, skipping options and their values."""
    skip = False
    for arg in args:
        if skip:
            skip = False
        elif arg in VALUE_FLAGS:
            skip = True
        elif not arg.startswith("-"):
            return arg
    return None


def classify(comm: str, argv: Sequence[str]) -> Tool | None:
    """The agent session a process is, by its kernel ``comm`` name and subcommand.

    Native Claude Code and Codex binaries are named ``claude`` and ``codex``;
    Codex's node launcher and helper processes (``codex-code-mode``) are not
    counted, so one session is one process. The same binaries also run servers
    and utilities (``codex app-server``, ``codex mcp-server``, ``claude mcp
    serve``), which are not sessions either. npm-installed Claude Code runs as
    ``node …/@anthropic-ai/claude-code/cli.js``.
    """
    if comm in _COMMS:
        tool, args = _COMMS[comm], argv[1:]
    elif comm in {"node", "bun"} and any("@anthropic-ai/claude-code" in a for a in argv[1:3]):
        tool, args = Tool.CLAUDE, argv[2:]
    else:
        return None
    if subcommand(args) in HELPER_SUBCOMMANDS.get(tool, frozenset()):
        return None
    return tool


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


def read_process(proc: Path, pid: int) -> AgentProcess | None:
    """Classify one process; ``None`` when it is not an agent session or vanished."""
    base = proc / str(pid)
    try:
        comm = (base / "comm").read_text(encoding="utf-8", errors="replace").strip()
        argv = [
            part.decode(errors="replace")
            for part in (base / "cmdline").read_bytes().split(b"\0")
            if part
        ]
    except OSError:
        return None
    tool = classify(comm, argv)
    if tool is None:
        return None
    try:
        env = environ_values((base / "environ").read_bytes())
    except OSError:
        env = {}
    try:
        cwd = str((base / "cwd").readlink())
    except OSError:
        cwd = ""
    return AgentProcess(pid, tool, env, model_flag(argv) or env.get("ANTHROPIC_MODEL"), cwd)


class ProcessScanner:
    """Incremental ``/proc`` scan: every new pid is read once, vanished pids forgotten.

    A pid keeps its classification for its lifetime; the rare process that is
    caught between fork and exec is corrected by the next ``full`` scan.
    """

    def __init__(self, proc: Path = Path("/proc")) -> None:
        self.proc = proc
        self._known: dict[int, AgentProcess | None] = {}

    def scan(self, *, full: bool = False) -> list[AgentProcess]:
        if full:
            self._known.clear()
        try:
            # Plain names, not a Path per process: this runs on every refresh.
            pids = {int(name) for name in os.listdir(self.proc) if name.isdigit()}  # noqa: PTH208
        except OSError:
            self._known.clear()
            return []
        for pid in self._known.keys() - pids:
            del self._known[pid]
        for pid in pids - self._known.keys():
            self._known[pid] = read_process(self.proc, pid)
        return sorted((p for p in self._known.values() if p is not None), key=lambda p: p.pid)


def scan_processes(proc: Path = Path("/proc")) -> list[AgentProcess]:
    return ProcessScanner(proc).scan()


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
