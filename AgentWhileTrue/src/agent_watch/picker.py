"""The interactive session picker.

The picker is a safety mechanism before it is a convenience. Nothing is
supervised that the user did not point at, and a plain shell is never
preselected however confident the discovery step feels, because preselection is
the one place where a classifier mistake turns into typing into a shell.

The interactive loop is kept separate from the pure parts - discovery, toggling
and rendering - so the decision logic is testable without a terminal.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

from agent_watch.classify import Classification, classify
from agent_watch.fsm import ProcessInspector
from agent_watch.proc import ProcessGoneError, ProcessInfo
from agent_watch.providers import for_process_class
from agent_watch.terminal.base import TerminalAdapter, TerminalError, TerminalSession

#: Interactive commands. Kept as data so the help text and the parser cannot
#: drift apart.
COMMANDS = (
    ("<number>", "toggle a session"),
    ("a", "select all detected agents"),
    ("n", "select none"),
    ("r", "rescan"),
    ("<enter>", "start watching the selected sessions"),
    ("q", "quit"),
)

_FZF_DELIMITER = "\t"


@dataclass(frozen=True, slots=True)
class Candidate:
    """One discovered session, with everything needed to display and select it."""

    session: TerminalSession
    info: ProcessInfo | None
    classification: Classification
    provider: str | None

    @property
    def key(self) -> str:
        return self.session.ref.key()

    @property
    def eligible(self) -> bool:
        """Whether this session may be supervised at all."""
        return self.provider is not None and self.classification.automatable

    @property
    def label(self) -> str:
        return (self.provider or self.classification.process_class.value).title()

    @property
    def tty(self) -> str:
        return self.info.tty if self.info else "-"

    @property
    def cwd(self) -> str:
        return self.info.cwd if self.info else "-"

    @property
    def note(self) -> str:
        """Why an ineligible session cannot be supervised."""
        if self.eligible:
            return ""
        return self.classification.blocker or self.classification.confidence.value.lower()


def discover(terminal: TerminalAdapter, inspector: ProcessInspector) -> list[Candidate]:
    """Enumerate every session the adapter can see and classify each one."""
    try:
        sessions = terminal.list_sessions()
    except TerminalError:
        return []
    candidates: list[Candidate] = []
    for session in sessions:
        info = inspector.inspect(session.foreground_pid)
        if info is None:
            continue
        try:
            classification = classify(info)
        except (OSError, ProcessGoneError):
            # A process can lose a thread or exit midway through classification.
            # Other Konsole sessions remain useful and must still be discovered.
            continue
        provider = for_process_class(classification.process_class)
        candidates.append(
            Candidate(
                session=session,
                info=info,
                classification=classification,
                provider=provider.name if provider else None,
            )
        )
    return candidates


def preselected(candidates: Iterable[Candidate]) -> set[str]:
    """Which sessions start ticked.

    Only high-confidence agent sessions. A plain shell is never preselected -
    vision section 5 says so, and it is the difference between a misclassified
    tab being ignored and being typed into.
    """
    return {candidate.key for candidate in candidates if candidate.eligible}


@dataclass(slots=True)
class PickerState:
    """The mutable half of the picker."""

    candidates: list[Candidate]
    selected: set[str] = field(default_factory=set)

    def toggle(self, index: int) -> bool:
        """Toggle by 1-based display index. Returns False for a bad index."""
        if not 1 <= index <= len(self.candidates):
            return False
        candidate = self.candidates[index - 1]
        if not candidate.eligible:
            # Refusing here rather than in the supervisor keeps the reason
            # visible to the person making the choice.
            return False
        if candidate.key in self.selected:
            self.selected.discard(candidate.key)
        else:
            self.selected.add(candidate.key)
        return True

    def select_all_agents(self) -> None:
        self.selected = preselected(self.candidates)

    def select_none(self) -> None:
        self.selected.clear()

    def chosen(self) -> list[Candidate]:
        return [candidate for candidate in self.candidates if candidate.key in self.selected]


def render(state: PickerState) -> str:
    """Render the picker as plain ANSI-free text.

    Deliberately plain: this has to be readable over SSH, in a pipe, and in a
    test failure message.
    """
    lines = ["Agent While True - select sessions to watch", ""]
    if not state.candidates:
        lines.append("  no Konsole sessions found")
    for index, candidate in enumerate(state.candidates, start=1):
        mark = "x" if candidate.key in state.selected else " "
        pid = candidate.session.foreground_pid
        row = (
            f" [{mark}] {index:<3} {candidate.label:<10} {candidate.tty:<8} "
            f"PID {pid:<8} {candidate.cwd}"
        )
        if candidate.note:
            row += f"   ({candidate.note})"
        lines.append(row)
    lines.append("")
    lines.extend(f"  {key:<9} {description}" for key, description in COMMANDS)
    return "\n".join(lines)


def _fzf_line(index: int, candidate: Candidate) -> str:
    return _FZF_DELIMITER.join(
        (
            str(index),
            candidate.label,
            candidate.tty,
            str(candidate.session.foreground_pid),
            candidate.cwd,
        )
    )


def fzf_available() -> bool:
    return shutil.which("fzf") is not None


def pick_with_fzf(candidates: Sequence[Candidate]) -> list[Candidate] | None:
    """Offer the eligible candidates through fzf.

    Returns ``None`` when fzf is unavailable or failed, so the caller falls back
    to the built-in picker. fzf stays strictly optional.
    """
    eligible = [candidate for candidate in candidates if candidate.eligible]
    if not eligible or not fzf_available():
        return None
    payload = "\n".join(_fzf_line(index, c) for index, c in enumerate(eligible, start=1))
    try:
        completed = subprocess.run(
            ["fzf", "--multi", "--with-nth=2..", f"--delimiter={_FZF_DELIMITER}"],
            input=payload,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return []
    chosen: list[Candidate] = []
    for line in completed.stdout.splitlines():
        head = line.split(_FZF_DELIMITER, 1)[0]
        if head.isdigit() and 1 <= int(head) <= len(eligible):
            chosen.append(eligible[int(head) - 1])
    return chosen


@dataclass(slots=True)
class NumberedPicker:
    """The built-in picker. Always available, never requires fzf."""

    read: Callable[[str], str] = input
    write: Callable[[str], None] = print

    def run(
        self,
        candidates: list[Candidate],
        *,
        rescan: Callable[[], list[Candidate]] | None = None,
    ) -> list[Candidate] | None:
        """Return the chosen candidates, or ``None`` if the user quit."""
        state = PickerState(candidates=candidates, selected=preselected(candidates))
        while True:
            self.write(render(state))
            try:
                raw = self.read("> ").strip().lower()
            except EOFError:
                # A closed stdin is not consent to watch anything.
                return None
            if raw in {"q", "quit"}:
                return None
            if raw == "":
                return state.chosen()
            if raw == "a":
                state.select_all_agents()
                continue
            if raw == "n":
                state.select_none()
                continue
            if raw == "r":
                if rescan is not None:
                    state.candidates = rescan()
                    state.selected &= {candidate.key for candidate in state.candidates}
                continue
            for token in raw.replace(",", " ").split():
                if token.isdigit():
                    state.toggle(int(token))
