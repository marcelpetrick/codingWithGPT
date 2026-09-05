"""The state vocabulary shared by the recognizers, the policy gate and the FSM."""

from __future__ import annotations

import enum


class SessionState(enum.StrEnum):
    """Where one supervised session currently is.

    The terminal states at the bottom never authorise input.
    """

    DISCOVERED = "DISCOVERED"
    ACTIVE = "ACTIVE"
    LIMIT_WARNING = "LIMIT_WARNING"
    LIMIT_BLOCKED = "LIMIT_BLOCKED"
    WAITING_FOR_RESET = "WAITING_FOR_RESET"
    RESET_GRACE_PERIOD = "RESET_GRACE_PERIOD"
    READY_TO_RESUME = "READY_TO_RESUME"
    CONTINUE_SENT = "CONTINUE_SENT"
    VERIFYING = "VERIFYING"

    UNSAFE = "UNSAFE"
    UNKNOWN = "UNKNOWN"
    PROCESS_GONE = "PROCESS_GONE"
    UNSUPPORTED = "UNSUPPORTED"

    @property
    def is_terminal(self) -> bool:
        return self in {
            SessionState.UNSAFE,
            SessionState.UNKNOWN,
            SessionState.PROCESS_GONE,
            SessionState.UNSUPPORTED,
        }


class ActionState(enum.StrEnum):
    """The lifecycle of one resume attempt.

    Persisting this is what stops a crash between "sent" and "recorded" from
    turning into a second keystroke after restart (vision DANGER 13).
    """

    PLANNED = "PLANNED"
    SENT = "SENT"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
