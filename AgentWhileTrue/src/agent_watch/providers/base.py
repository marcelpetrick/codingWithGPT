"""Provider-agnostic prompt recognition.

A recognizer turns a bounded window of displayed text into a
:class:`Recognition`: which known patterns matched, what state that implies,
which limit windows are involved, when the limit is expected to reset, and what
action - if any - the pattern says would resume the session.

Two rules from the vision are structural here:

* a single regex match never authorises input, so an action is only ever
  *proposed*; the policy gate in :mod:`agent_watch.policy` decides;
* unknown layouts produce no action at all rather than a guessed one.
"""

from __future__ import annotations

import enum
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from agent_watch.logging_setup import fingerprint
from agent_watch.providers.timeparse import parse_reset
from agent_watch.states import SessionState

#: How many of the most recent displayed lines count as "live". Text above this
#: is treated as scrolled-away history and cannot trigger anything, which is the
#: cheap half of the defence against acting on an old banner (DANGER 3).
DEFAULT_LIVE_LINES = 30


class PromptKind(enum.StrEnum):
    """What a matched pattern means."""

    LIMIT_WARNING = "LIMIT_WARNING"
    LIMIT_BLOCKED = "LIMIT_BLOCKED"
    READY_TO_RESUME = "READY_TO_RESUME"
    #: The provider says it will resume itself. Claude Code has done this by
    #: default since 2.1.234, and a supervisor that also presses Enter would be
    #: racing it.
    SELF_HEALING = "SELF_HEALING"
    #: The provider will *not* resume itself - the reset is far out, or the
    #: session was backgrounded. This is the gap the supervisor exists to fill.
    WILL_NOT_SELF_RESUME = "WILL_NOT_SELF_RESUME"
    PAID_ACTION_REQUIRED = "PAID_ACTION_REQUIRED"
    MODEL_DOWNGRADE_OFFER = "MODEL_DOWNGRADE_OFFER"


class ActionKind(enum.StrEnum):
    """The mechanical form of a resume action."""

    #: Press Enter. Used only where the provider displays an explicit
    #: "press enter to continue" affordance.
    ENTER = "ENTER"
    #: Type text, then press Enter. Strictly more dangerous, because if the
    #: foreground process changed the text lands in a shell.
    TEXT_THEN_ENTER = "TEXT_THEN_ENTER"
    #: Move from a visibly selected first menu item to the exact safe second
    #: item and confirm it. Used only to arm Claude's own automatic wait.
    ARROW_DOWN_THEN_ENTER = "ARROW_DOWN_THEN_ENTER"


@dataclass(frozen=True, slots=True)
class ResumeAction:
    """What a pattern says would resume the session."""

    kind: ActionKind
    text: str = ""
    #: Name of the :class:`~agent_watch.config.Policy` flag that must be true
    #: before this action may run unattended. ``None`` means the general
    #: ``resume_after_reset`` policy is enough.
    requires_policy: str | None = None

    def keystrokes(self) -> str:
        """The exact bytes to hand to the terminal adapter."""
        if self.kind is ActionKind.ENTER:
            return "\r"
        if self.kind is ActionKind.ARROW_DOWN_THEN_ENTER:
            return "\x1b[B\r"
        return f"{self.text}\r"


@dataclass(frozen=True, slots=True)
class PromptPattern:
    """One versioned, testable description of a provider prompt.

    ``all_of`` must *all* appear inside the live window for the pattern to
    match, which is how a pattern can require an anchor as well as a headline
    and so avoid firing on a passing mention.
    """

    id: str
    provider: str
    kind: PromptKind
    all_of: tuple[re.Pattern[str], ...]
    #: Which limit window this pattern is about ("session", "weekly", "opus",
    #: "credits", ...). Used so that a five-hour reset cannot unblock a session
    #: whose weekly limit is still exhausted (vision section 25).
    scope: str = "unknown"
    action: ResumeAction | None = None
    #: Free-text note kept for `doctor` and for future pattern archaeology.
    note: str = ""
    #: Provider version this pattern was verified against.
    verified_against: str = ""

    def match(self, windows: tuple[str, ...]) -> bool:
        """Match if every anchor is found in at least one window rendering.

        Several renderings are offered because a terminal soft-wraps long lines:
        "…so this task will not\nresume on its own" is one provider sentence but
        two screen lines, and a pattern that only ever saw the line-joined form
        would miss exactly the prompts that matter most.
        """
        return all(any(pattern.search(window) for window in windows) for pattern in self.all_of)


@dataclass(frozen=True, slots=True)
class PromptMatch:
    """A pattern that matched, with just enough text to parse a reset time.

    ``line`` is the screen line that triggered the match and ``context`` adds the
    line after it, because a soft wrap can push the reset time onto the
    continuation line. Nothing wider than this is retained, and neither field is
    ever logged or persisted.
    """

    pattern: PromptPattern
    line: str
    context: str = ""

    @property
    def id(self) -> str:
        return self.pattern.id


@dataclass(frozen=True, slots=True)
class Recognition:
    """The full reading of one screen.

    Carries no terminal text beyond the single matched line, which is used only
    for reset-time parsing and is never logged or persisted.
    """

    provider: str
    state: SessionState
    matches: tuple[PromptMatch, ...] = field(default_factory=tuple)
    reset_at: datetime | None = None
    screen_fingerprint: str = ""
    blocked_scopes: frozenset[str] = frozenset()
    vetoes: tuple[str, ...] = ()

    @property
    def matched_ids(self) -> tuple[str, ...]:
        return tuple(match.id for match in self.matches)

    @property
    def action(self) -> ResumeAction | None:
        """The proposed action, if exactly one pattern proposes one.

        Ambiguity is not resolved by preference order: two patterns proposing
        different actions means the screen was not understood.
        """
        actions = [match.pattern.action for match in self.matches if match.pattern.action]
        unique = {(action.kind, action.text) for action in actions}
        if len(unique) != 1:
            return None
        return actions[0]


def _matched_text(lines: list[str], pattern: PromptPattern) -> tuple[str, str]:
    """Return the triggering line and that line joined with its successor."""
    for index in range(len(lines) - 1, -1, -1):
        line = lines[index]
        if any(candidate.search(line) for candidate in pattern.all_of):
            successor = lines[index + 1] if index + 1 < len(lines) else ""
            return line, f"{line.rstrip()} {successor.strip()}".strip()
    return "", ""


def _windows(lines: list[str]) -> tuple[str, ...]:
    """Render the live screen the two ways a pattern may need to see it.

    The first keeps line structure; the second undoes soft wrapping by joining
    every line with a single space, so a sentence broken across a wrap is still
    one string.
    """
    return ("\n".join(lines), " ".join(line.strip() for line in lines))


class ProviderAdapter(ABC):
    """Recognises one provider's prompts."""

    #: Provider identifier, e.g. ``"claude"``.
    name: str = "abstract"
    #: Bumped whenever the pattern table changes, so logs say which table
    #: produced a decision (vision DANGER 11).
    patterns_version: str = "0"

    @property
    @abstractmethod
    def patterns(self) -> tuple[PromptPattern, ...]:
        """The pattern table for this provider."""

    @abstractmethod
    def executable_names(self) -> frozenset[str]:
        """Executable basenames that identify this provider."""

    def recognise(
        self,
        lines: list[str],
        *,
        now: datetime,
        live_lines: int = DEFAULT_LIVE_LINES,
    ) -> Recognition:
        """Read a bounded screen window into a :class:`Recognition`."""
        live = lines[-live_lines:]
        windows = _windows(live)
        matches = []
        for pattern in self.patterns:
            if not pattern.match(windows):
                continue
            line, context = _matched_text(live, pattern)
            matches.append(PromptMatch(pattern=pattern, line=line, context=context))
        matches = tuple(matches)
        return Recognition(
            provider=self.name,
            state=self._derive_state(matches),
            matches=matches,
            reset_at=self._derive_reset(matches, now=now),
            screen_fingerprint=fingerprint(live),
            blocked_scopes=frozenset(
                match.pattern.scope
                for match in matches
                if match.pattern.kind is PromptKind.LIMIT_BLOCKED
            ),
            vetoes=self._derive_vetoes(matches),
        )

    @staticmethod
    def _derive_state(matches: tuple[PromptMatch, ...]) -> SessionState:
        kinds = {match.pattern.kind for match in matches}
        if PromptKind.READY_TO_RESUME in kinds:
            return SessionState.READY_TO_RESUME
        if PromptKind.LIMIT_BLOCKED in kinds:
            return SessionState.LIMIT_BLOCKED
        if PromptKind.WILL_NOT_SELF_RESUME in kinds:
            return SessionState.WAITING_FOR_RESET
        if PromptKind.LIMIT_WARNING in kinds:
            return SessionState.LIMIT_WARNING
        if kinds & {PromptKind.PAID_ACTION_REQUIRED, PromptKind.MODEL_DOWNGRADE_OFFER}:
            # A paid or downgrade prompt on its own is still a blocking prompt;
            # it just has no permitted action.
            return SessionState.LIMIT_BLOCKED
        if PromptKind.SELF_HEALING in kinds:
            return SessionState.WAITING_FOR_RESET
        return SessionState.ACTIVE

    @staticmethod
    def _derive_vetoes(matches: tuple[PromptMatch, ...]) -> tuple[str, ...]:
        vetoes: list[str] = []
        for match in matches:
            if match.pattern.kind is PromptKind.PAID_ACTION_REQUIRED:
                vetoes.append(f"paid-action-required:{match.id}")
            elif match.pattern.kind is PromptKind.MODEL_DOWNGRADE_OFFER:
                vetoes.append(f"model-downgrade-offer:{match.id}")
            elif match.pattern.kind is PromptKind.SELF_HEALING:
                vetoes.append(f"provider-resumes-itself:{match.id}")
        return tuple(vetoes)

    @staticmethod
    def _derive_reset(matches: tuple[PromptMatch, ...], *, now: datetime) -> datetime | None:
        interesting = {
            PromptKind.LIMIT_BLOCKED,
            PromptKind.WILL_NOT_SELF_RESUME,
            PromptKind.LIMIT_WARNING,
        }
        candidates = []
        for match in matches:
            if match.pattern.kind not in interesting:
                continue
            # Prefer the triggering line; fall back to it plus its successor,
            # which is where a soft wrap puts the time.
            parsed = parse_reset(match.line, now) or parse_reset(match.context, now)
            if parsed is not None:
                candidates.append(parsed)
        # The latest reset wins: if both a five-hour and a weekly limit are on
        # screen, the session is not usable until the later one clears.
        return max(candidates) if candidates else None
