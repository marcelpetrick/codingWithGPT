"""Tests for foreground-process classification.

The fixtures mirror processes captured on a live machine: Claude Code 2.1.261
runs as a native binary under ``~/.local/share/claude/versions/``, while Codex
CLI 0.153.2 is a Node shim that execs a native child.
"""

from __future__ import annotations

import pytest

from agent_watch import classify as classify_module
from agent_watch.classify import Confidence, ProcessClass, classify

CLAUDE_EXE = "/home/user/.local/share/claude/versions/2.1.261"
CODEX_SHIM = "/run/user/1000/fnm_multishells/631816_1788536739178/bin/codex"
CODEX_NATIVE = (
    "/home/user/.local/share/fnm/node-versions/v20.20.1/installation/lib/node_modules"
    "/@openai/codex/node_modules/@openai/codex-linux-x64/vendor"
    "/x86_64-unknown-linux-musl/bin/codex"
)


def test_real_claude_process_is_automatable(info_factory) -> None:
    info = info_factory(
        comm="claude",
        exe=CLAUDE_EXE,
        cmdline=("claude", "--dangerously-skip-permissions", "--resume"),
    )
    result = classify(info)
    assert result.process_class is ProcessClass.CLAUDE
    assert result.confidence is Confidence.HIGH
    assert result.automatable


def test_codex_node_shim_is_recognised_despite_comm_being_node(info_factory, monkeypatch) -> None:
    monkeypatch.setattr(classify_module, "_child_comms", lambda pid: ("codex",))
    info = info_factory(
        comm="node",
        exe="/home/user/.local/share/fnm/node-versions/v20.20.1/installation/bin/node",
        cmdline=("node", CODEX_SHIM, "--dangerously-bypass-approvals-and-sandbox", "resume"),
    )
    result = classify(info)
    assert result.process_class is ProcessClass.CODEX
    assert result.confidence is Confidence.HIGH
    assert result.automatable


def test_native_codex_child_is_recognised(info_factory) -> None:
    info = info_factory(comm="codex", exe=CODEX_NATIVE, cmdline=(CODEX_NATIVE, "resume"))
    result = classify(info)
    assert result.process_class is ProcessClass.CODEX
    assert result.automatable


@pytest.mark.parametrize("shell", ["zsh", "bash", "fish", "sh"])
def test_idle_shell_is_never_automatable(info_factory, shell: str) -> None:
    result = classify(info_factory(comm=shell, exe=f"/usr/bin/{shell}", cmdline=(shell,)))
    assert result.process_class is ProcessClass.SHELL
    assert not result.automatable
    assert result.blocker == "idle-shell"


def test_ssh_environment_blocks_even_a_convincing_agent(info_factory) -> None:
    info = info_factory(
        comm="claude",
        exe=CLAUDE_EXE,
        cmdline=("claude",),
        environ_keys=frozenset({"SSH_TTY", "SSH_CONNECTION"}),
    )
    result = classify(info)
    assert result.process_class is ProcessClass.SSH
    assert not result.automatable


def test_tmux_environment_blocks_automation(info_factory) -> None:
    info = info_factory(
        comm="claude",
        exe=CLAUDE_EXE,
        cmdline=("claude",),
        environ_keys=frozenset({"TMUX", "TMUX_PANE"}),
    )
    result = classify(info)
    assert result.process_class is ProcessClass.TMUX
    assert not result.automatable


def test_screen_environment_blocks_automation(info_factory) -> None:
    info = info_factory(comm="zsh", environ_keys=frozenset({"STY"}))
    assert classify(info).process_class is ProcessClass.SCREEN


def test_container_marker_blocks_automation(info_factory, monkeypatch) -> None:
    monkeypatch.setattr(classify_module, "_detect_container", lambda info: "container-cgroup")
    result = classify(info_factory(comm="claude", exe=CLAUDE_EXE, cmdline=("claude",)))
    assert result.process_class is ProcessClass.CONTAINER
    assert not result.automatable


def test_tmux_ancestor_blocks_a_genuine_agent(info_factory, monkeypatch) -> None:
    monkeypatch.setattr(
        classify_module, "_ancestor_blocker", lambda info: "nested-terminal-ancestor=tmux"
    )
    result = classify(info_factory(comm="claude", exe=CLAUDE_EXE, cmdline=("claude",)))
    assert result.process_class is ProcessClass.CLAUDE
    assert result.blocker == "nested-terminal-ancestor=tmux"
    assert not result.automatable


def test_a_single_weak_signal_is_not_enough_to_automate(info_factory) -> None:
    # Only one signal: the executable happens to be named `claude`, nothing else
    # corroborates it. The vision requires more than one process field.
    info = info_factory(comm="wrapper", exe="/opt/vendor/claude", cmdline=("wrapper",))
    result = classify(info)
    assert result.process_class is ProcessClass.CLAUDE
    assert result.confidence is Confidence.LOW
    assert not result.automatable


def test_contradictory_evidence_fails_closed(info_factory) -> None:
    info = info_factory(comm="claude", exe=CODEX_NATIVE, cmdline=("claude", "codex"))
    result = classify(info)
    assert result.process_class is ProcessClass.UNKNOWN
    assert result.blocker == "ambiguous-provider-evidence"
    assert not result.automatable


def test_editor_is_blocked(info_factory) -> None:
    result = classify(info_factory(comm="nvim", exe="/usr/bin/nvim", cmdline=("nvim",)))
    assert result.process_class is ProcessClass.EDITOR
    assert not result.automatable


def test_unrecognised_process_fails_closed(info_factory) -> None:
    result = classify(info_factory(comm="btop", exe="/usr/bin/btop", cmdline=("btop",)))
    assert result.process_class is ProcessClass.UNKNOWN
    assert result.blocker == "unrecognised-process"
    assert not result.automatable
