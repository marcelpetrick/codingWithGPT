"""Classify the foreground process of a terminal session.

Only a process that is *positively* identified as Codex or Claude Code may ever
receive injected input. Everything else - an idle shell, an editor, an SSH
client, a tmux server, anything inside a container - must disable automation
rather than merely be treated as uninteresting (vision sections 12 and 16, and
DANGER 6, 7, 8, 16).

Classification never rests on a single process field. Wrappers change: Codex in
particular ships as a Node shim whose ``comm`` is ``node`` and whose real
binary is a child process. A verdict of CODEX or CLAUDE therefore requires at
least two independent corroborating signals before it is considered actionable.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path

from agent_watch import proc
from agent_watch.proc import ProcessInfo

#: Two independent signals are required before a verdict may drive automation.
MIN_SIGNALS_FOR_HIGH_CONFIDENCE = 2

#: How far up the process tree ancestry checks walk before giving up.
MAX_ANCESTOR_DEPTH = 12


class ProcessClass(enum.StrEnum):
    """What the foreground process of a session is."""

    CODEX = "CODEX"
    CLAUDE = "CLAUDE"
    SHELL = "SHELL"
    SSH = "SSH"
    TMUX = "TMUX"
    SCREEN = "SCREEN"
    CONTAINER = "CONTAINER"
    EDITOR = "EDITOR"
    UNKNOWN = "UNKNOWN"

    @property
    def is_agent(self) -> bool:
        return self in {ProcessClass.CODEX, ProcessClass.CLAUDE}


class Confidence(enum.StrEnum):
    """How strongly the evidence supports the verdict."""

    HIGH = "HIGH"
    LOW = "LOW"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class Classification:
    """The verdict plus the evidence that produced it.

    The signal list exists so that a refusal can be explained in the log and in
    ``agent-watch doctor`` without ever quoting terminal content.
    """

    process_class: ProcessClass
    confidence: Confidence
    signals: tuple[str, ...] = field(default_factory=tuple)
    blocker: str | None = None

    @property
    def automatable(self) -> bool:
        """Whether this session may receive injected input at all."""
        return (
            self.process_class.is_agent
            and self.confidence is Confidence.HIGH
            and self.blocker is None
        )


#: Foreground processes that must switch automation off. An idle shell is the
#: dangerous case: typing "continue" into Zsh runs whatever that resolves to.
_SHELLS = frozenset({"zsh", "bash", "sh", "fish", "dash", "ksh", "tcsh", "csh"})
_EDITORS = frozenset({"vim", "nvim", "vi", "emacs", "nano", "helix", "hx", "kak", "micro"})
_NESTED_TERMINALS = {
    "tmux": ProcessClass.TMUX,
    "tmux:server": ProcessClass.TMUX,
    "screen": ProcessClass.SCREEN,
    "screen.real": ProcessClass.SCREEN,
}
_REMOTE = frozenset({"ssh", "sshd", "mosh", "mosh-client", "et", "autossh"})
_OTHER_KNOWN = frozenset({"sudo", "su", "doas", "python", "python3", "node", "git", "less", "man"})

_CONTAINER_CGROUP_MARKERS = ("docker", "podman", "libpod", "containerd", "lxc", "kubepods")
_CONTAINER_FILES = (Path("/.dockerenv"), Path("/run/.containerenv"))


def _basename(value: str) -> str:
    return Path(value).name if value else ""


def _detect_container(info: ProcessInfo) -> str | None:
    """Return a reason string when the process looks containerised.

    Namespaced PIDs make ``/proc`` identity assumptions unsafe, so an obvious
    container is refused rather than guessed at (vision DANGER 8).
    """
    if "container" in info.environ_keys or "DISTROBOX_ENTER_PATH" in info.environ_keys:
        return "container-environment-marker"
    try:
        cgroup_path = proc.PROC / str(info.pid) / "cgroup"
        cgroup = cgroup_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        cgroup = ""
    lowered = cgroup.lower()
    if any(marker in lowered for marker in _CONTAINER_CGROUP_MARKERS):
        return "container-cgroup"
    if any(path.exists() for path in _CONTAINER_FILES):
        return "container-runtime-file"
    return None


def _detect_remote(info: ProcessInfo) -> str | None:
    """Return a reason string when the session is (or sits under) SSH."""
    if _basename(info.comm) in _REMOTE:
        return "ssh-foreground-process"
    if {"SSH_TTY", "SSH_CONNECTION", "SSH_CLIENT"} & info.environ_keys:
        return "ssh-environment-marker"
    return None


def _detect_nested_terminal(info: ProcessInfo) -> tuple[ProcessClass, str] | None:
    """Return the class and reason when a multiplexer hides other panes."""
    nested = _NESTED_TERMINALS.get(info.comm)
    if nested is not None:
        return nested, f"{nested.value.lower()}-foreground-process"
    if "TMUX" in info.environ_keys or "TMUX_PANE" in info.environ_keys:
        return ProcessClass.TMUX, "tmux-environment-marker"
    if "STY" in info.environ_keys:
        return ProcessClass.SCREEN, "screen-environment-marker"
    return None


def _claude_signals(info: ProcessInfo) -> list[str]:
    signals: list[str] = []
    if info.comm == "claude":
        signals.append("comm=claude")
    argv0 = _basename(info.cmdline[0]) if info.cmdline else ""
    if argv0 == "claude":
        signals.append("argv0=claude")
    exe = info.exe
    if "/claude/versions/" in exe or _basename(exe) == "claude":
        signals.append("exe-under-claude-versions")
    if any(_basename(arg) == "claude" for arg in info.cmdline[1:2]):
        # `node .../bin/claude` style launchers.
        signals.append("argv1=claude")
    return signals


def _codex_signals(info: ProcessInfo, child_comms: tuple[str, ...]) -> list[str]:
    signals: list[str] = []
    if info.comm == "codex":
        signals.append("comm=codex")
    argv0 = _basename(info.cmdline[0]) if info.cmdline else ""
    if argv0 == "codex":
        signals.append("argv0=codex")
    if "@openai/codex" in info.exe or _basename(info.exe) == "codex":
        signals.append("exe-under-openai-codex")
    # The published Codex CLI is a Node shim: `node <path>/bin/codex …`.
    if argv0 == "node" and any(_basename(arg) == "codex" for arg in info.cmdline[1:]):
        signals.append("node-shim-argv=codex")
    if any(arg.endswith("/@openai/codex/bin/codex.js") for arg in info.cmdline):
        signals.append("node-shim-script=codex.js")
    if "codex" in child_comms:
        signals.append("native-child=codex")
    return signals


def _child_comms(pid: int) -> tuple[str, ...]:
    try:
        kids = proc.children(pid)
    except OSError:
        return ()
    return tuple(proc.read_comm(kid) for kid in kids)


def _ancestor_blocker(info: ProcessInfo) -> str | None:
    """Walk up the tree looking for a multiplexer or SSH between us and Konsole.

    ``konsole -> zsh -> tmux -> zsh -> claude`` must not be automated even
    though the foreground process really is Claude: the visible pane is not
    necessarily the one being written to.
    """
    pid = info.ppid
    for _ in range(MAX_ANCESTOR_DEPTH):
        if pid <= 1 or not proc.exists(pid):
            return None
        comm = proc.read_comm(pid)
        if comm in _NESTED_TERMINALS:
            return f"nested-terminal-ancestor={comm}"
        if comm in _REMOTE:
            return f"remote-ancestor={comm}"
        if comm == "konsole":
            return None
        pid = proc.read_ppid(pid)
    return None


def classify(info: ProcessInfo) -> Classification:
    """Classify one foreground process.

    Blockers are evaluated before agent detection, so a Claude process running
    inside tmux or over SSH is reported as unsupported rather than as an
    automatable agent.
    """
    if (reason := _detect_container(info)) is not None:
        return Classification(ProcessClass.CONTAINER, Confidence.HIGH, (reason,), blocker=reason)
    if (reason := _detect_remote(info)) is not None:
        return Classification(ProcessClass.SSH, Confidence.HIGH, (reason,), blocker=reason)
    if (nested := _detect_nested_terminal(info)) is not None:
        klass, reason = nested
        return Classification(klass, Confidence.HIGH, (reason,), blocker=reason)

    blocker = _ancestor_blocker(info)
    child_comms = _child_comms(info.pid)

    claude = _claude_signals(info)
    codex = _codex_signals(info, child_comms)

    if claude and codex:
        # Contradictory evidence is not a tie to break; it is a reason to stop.
        return Classification(
            ProcessClass.UNKNOWN,
            Confidence.NONE,
            tuple(claude + codex),
            blocker="ambiguous-provider-evidence",
        )
    for klass, signals in ((ProcessClass.CLAUDE, claude), (ProcessClass.CODEX, codex)):
        if signals:
            confidence = (
                Confidence.HIGH
                if len(signals) >= MIN_SIGNALS_FOR_HIGH_CONFIDENCE
                else Confidence.LOW
            )
            return Classification(klass, confidence, tuple(signals), blocker=blocker)

    if info.comm in _SHELLS:
        return Classification(
            ProcessClass.SHELL, Confidence.HIGH, (f"comm={info.comm}",), blocker="idle-shell"
        )
    if info.comm in _EDITORS:
        return Classification(
            ProcessClass.EDITOR, Confidence.HIGH, (f"comm={info.comm}",), blocker="editor"
        )
    if info.comm in _OTHER_KNOWN:
        return Classification(
            ProcessClass.UNKNOWN,
            Confidence.NONE,
            (f"comm={info.comm}",),
            blocker="not-an-agent-process",
        )
    return Classification(
        ProcessClass.UNKNOWN,
        Confidence.NONE,
        (f"comm={info.comm}",),
        blocker="unrecognised-process",
    )
