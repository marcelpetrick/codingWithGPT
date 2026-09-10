# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

import pytest

from tokenusage2.model import Account, Tool
from tokenusage2.procscan import (
    AgentProcess,
    classify,
    model_flag,
    running_by_account,
    scan_processes,
    subcommand,
)


def make_process(
    root: Path,
    pid: int,
    comm: str,
    argv: list[str],
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> None:
    directory = root / str(pid)
    directory.mkdir(parents=True)
    (directory / "comm").write_text(comm + "\n")
    (directory / "cmdline").write_bytes(b"\0".join(arg.encode() for arg in argv) + b"\0")
    if env is not None:
        (directory / "environ").write_bytes(
            b"\0".join(f"{key}={value}".encode() for key, value in env.items())
        )
    if cwd is not None:
        (directory / "cwd").symlink_to(cwd)


def test_scan_processes_reads_only_the_wanted_variables(tmp_path: Path) -> None:
    proc = tmp_path / "proc"
    make_process(
        proc,
        10,
        "claude",
        ["claude", "--model", "north"],
        {
            "CLAUDE_CONFIG_DIR": "/c",
            "ANTHROPIC_BASE_URL": "http://gpu:11434",
            "ANTHROPIC_API_KEY": "sk-secret",
        },
        cwd=tmp_path,
    )
    make_process(proc, 11, "node", ["node", "/x/bin/codex"], {})
    make_process(proc, 12, "codex", ["/x/codex"], {"CODEX_HOME": "/w"})
    make_process(proc, 13, "codex-code-mode", ["/x/codex-code-mode-host"], {})
    make_process(proc, 14, "node", ["node", "/lib/node_modules/@anthropic-ai/claude-code/cli.js"])
    make_process(proc, 15, "opencode", ["opencode"], {})
    (proc / "self").mkdir()
    (proc / "99").mkdir()
    found = scan_processes(proc)
    assert [(p.pid, p.tool) for p in found] == [
        (10, Tool.CLAUDE),
        (12, Tool.CODEX),
        (14, Tool.CLAUDE),
        (15, Tool.OPENCODE),
    ]
    claude = found[0]
    assert claude.env == {"CLAUDE_CONFIG_DIR": "/c", "ANTHROPIC_BASE_URL": "http://gpu:11434"}
    assert claude.model == "north"
    assert claude.cwd == str(tmp_path)
    assert found[2].env == {}
    assert scan_processes(tmp_path / "missing") == []


def test_classify_and_model_flag() -> None:
    assert classify("claude", ["claude"]) is Tool.CLAUDE
    assert classify("bash", ["bash"]) is None
    assert model_flag(["x", "--model=m"]) == "m"
    assert model_flag(["--model"]) is None


def test_running_by_account(tmp_path: Path) -> None:
    accounts = [
        Account("c", Tool.CLAUDE, tmp_path / ".claude", "claude"),
        Account("w", Tool.CODEX, tmp_path / ".codex-w", "w"),
        Account("o", Tool.OPENCODE, tmp_path / "oc.db", "opencode"),
    ]
    processes = [
        AgentProcess(1, Tool.CLAUDE),
        AgentProcess(2, Tool.CLAUDE),
        AgentProcess(3, Tool.CODEX, {"CODEX_HOME": "~/.codex-w"}),
        AgentProcess(4, Tool.CODEX),
        AgentProcess(5, Tool.OPENCODE),
    ]
    assert running_by_account(processes, accounts, tmp_path, {}) == {"c": 2, "w": 1, "o": 1}
    assert running_by_account([AgentProcess(6, Tool.OPENCODE)], [], tmp_path, {}) == {}


@pytest.mark.parametrize(
    ("comm", "argv", "expected"),
    [
        ("codex", ["codex"], Tool.CODEX),
        ("codex", ["codex", "--dangerously-bypass-approvals-and-sandbox", "resume"], Tool.CODEX),
        ("codex", ["codex", "exec", "fix the tests"], Tool.CODEX),
        ("codex", ["codex", "-m", "app-server"], Tool.CODEX),
        ("codex", ["codex", "app-server"], None),
        ("codex", ["codex", "-c", "model=x", "mcp-server"], None),
        ("codex", ["codex", "login"], None),
        ("claude", ["claude", "--model", "opus", "explain"], Tool.CLAUDE),
        ("claude", ["claude", "mcp", "serve"], None),
        ("node", ["node", "/lib/@anthropic-ai/claude-code/cli.js", "doctor"], None),
        ("node", ["node", "/lib/@anthropic-ai/claude-code/cli.js", "-p", "hi"], Tool.CLAUDE),
    ],
)
def test_helper_subcommands_are_not_sessions(
    comm: str, argv: list[str], expected: Tool | None
) -> None:
    assert classify(comm, argv) is expected


def test_subcommand() -> None:
    assert subcommand([]) is None
    assert subcommand(["--yolo", "-c", "a=b", "resume", "x"]) == "resume"
    assert subcommand(["--model"]) is None
