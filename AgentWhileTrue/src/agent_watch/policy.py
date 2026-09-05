"""The resume gate.

This module answers exactly one question: *may the supervisor type into this
session right now?* Section 17 of the vision lists the conditions; section 45
states the rule they serve - act only when it is known what process is being
controlled, which session owns it, why it is blocked, when usage returns, what
input the prompt expects, whether policy permits it, and whether it was already
attempted.

Every condition is a separate, named check that returns a refusal reason rather
than a bare ``False``. That shape matters: a refusal that cannot say why is a
refusal nobody can debug, and the log needs the reason more than it needs the
verdict.
"""

from __future__ import annotations

import enum
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from agent_watch.classify import Classification
from agent_watch.config import Config, Mode
from agent_watch.proc import ProcessIdentity
from agent_watch.providers.base import ActionKind, Recognition, ResumeAction
from agent_watch.quota import Availability, QuotaSnapshot
from agent_watch.states import SessionState
from agent_watch.terminal.base import SessionRef


class Authorization(enum.StrEnum):
    """How strongly the evidence says usage is actually available again."""

    #: The provider itself says so - a fresh quota snapshot reporting available
    #: usage, or the provider's own "usage limit has reset" affordance.
    PROVIDER_CONFIRMED = "PROVIDER_CONFIRMED"
    #: Only a wall-clock reset time plus the grace period has elapsed. A nominal
    #: reset can pass while usage is still unavailable, so this is weaker.
    TIME_ONLY = "TIME_ONLY"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class ResumeRequest:
    """Everything the gate is allowed to consider.

    Assembling this explicitly is deliberate: the gate cannot reach out and
    fetch anything, so it cannot accidentally depend on state the caller did not
    revalidate.
    """

    now: datetime
    config: Config
    selected: bool
    selected_ref: SessionRef
    live_ref: SessionRef
    selected_identity: ProcessIdentity
    live_identity: ProcessIdentity | None
    classification: Classification
    recognition: Recognition
    quota: QuotaSnapshot
    attempts: int = 0
    actioned_fingerprints: frozenset[str] = frozenset()
    marked_unsafe: bool = False


@dataclass(frozen=True, slots=True)
class Decision:
    """The gate's answer."""

    allowed: bool
    reason: str
    action: ResumeAction | None = None
    authorization: Authorization = Authorization.NONE
    #: True in ask mode: the action is permissible but a human must confirm.
    requires_confirmation: bool = False
    #: When the gate refused only because it is too early, this is the earliest
    #: instant worth re-checking. Lets the loop sleep instead of spinning.
    retry_at: datetime | None = None
    idempotency_key: str = ""


def idempotency_key(request: ResumeRequest) -> str:
    """A key identifying one logical prompt on one process in one session.

    Includes the process start time, so a restarted agent in the same tab and
    the same directory is a different prompt (vision DANGER 18), and the screen
    fingerprint, so one prompt yields at most one action (DANGER 17).
    """
    identity = request.live_identity or request.selected_identity
    material = "|".join(
        (
            request.recognition.provider,
            request.live_ref.key(),
            identity.key(),
            request.recognition.screen_fingerprint,
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


# -- individual conditions -------------------------------------------------
# Each returns a refusal reason, or None to mean "this condition is satisfied".

_ACTIONABLE_STATES = frozenset(
    {SessionState.LIMIT_BLOCKED, SessionState.READY_TO_RESUME, SessionState.WAITING_FOR_RESET}
)


def _check_selected(request: ResumeRequest) -> str | None:
    if not request.selected:
        return "session-not-selected-by-user"
    return None


def _check_not_unsafe(request: ResumeRequest) -> str | None:
    if request.marked_unsafe:
        return "session-marked-unsafe"
    return None


def _check_same_session(request: ResumeRequest) -> str | None:
    if request.live_ref != request.selected_ref:
        return "konsole-session-changed"
    return None


def _check_same_process(request: ResumeRequest) -> str | None:
    if request.live_identity is None:
        return "process-gone"
    if request.live_identity != request.selected_identity:
        # PID reuse, or the agent exited and something else took the foreground.
        return "process-identity-changed"
    return None


def _check_is_agent(request: ResumeRequest) -> str | None:
    classification = request.classification
    if not classification.automatable:
        return f"not-automatable:{classification.blocker or classification.confidence.value}"
    return None


def _check_provider_matches(request: ResumeRequest) -> str | None:
    expected = request.classification.process_class.value.lower()
    if request.recognition.provider != expected:
        return "provider-mismatch"
    return None


def _check_recognised_prompt(request: ResumeRequest) -> str | None:
    if request.recognition.state not in _ACTIONABLE_STATES:
        return f"no-recognised-blocking-prompt:{request.recognition.state.value}"
    return None


def _check_no_veto(request: ResumeRequest) -> str | None:
    vetoes = request.recognition.vetoes
    action = request.recognition.action
    if action is not None and action.kind is ActionKind.ARROW_DOWN_THEN_ENTER:
        # The exact menu action selects item 2. Merely displaying item 3's paid
        # upgrade is therefore not ambiguous, but every other veto still is.
        vetoes = tuple(
            veto for veto in vetoes if veto != "paid-action-required:claude/upgrade-plan-offer"
        )
    if vetoes:
        return vetoes[0]
    return None


def _check_policy_allows_resume(request: ResumeRequest) -> str | None:
    if not request.config.policy.resume_after_reset:
        return "policy-disallows-resume"
    return None


def _check_action_exists(request: ResumeRequest) -> str | None:
    if request.recognition.action is None:
        # Either no pattern proposed one, or two proposed different ones. Both
        # mean the screen was not understood well enough to type into it.
        return "no-unambiguous-action-for-prompt"
    return None


def _check_action_policy(request: ResumeRequest) -> str | None:
    action = request.recognition.action
    if action is None or action.requires_policy is None:
        return None
    if not getattr(request.config.policy, action.requires_policy, False):
        return f"action-requires-policy:{action.requires_policy}"
    return None


def _check_not_already_actioned(request: ResumeRequest) -> str | None:
    if idempotency_key(request) in request.actioned_fingerprints:
        return "already-actioned"
    return None


def _check_attempts(request: ResumeRequest) -> str | None:
    if request.attempts >= request.config.max_resume_attempts:
        return "max-resume-attempts-reached"
    return None


def _check_no_other_limit(request: ResumeRequest) -> str | None:
    """A reset of one window must not resume a session another window blocks."""
    action = request.recognition.action
    if action is not None and action.kind is ActionKind.ARROW_DOWN_THEN_ENTER:
        return None
    still_exhausted = request.quota.exhausted_scopes
    if not still_exhausted:
        return None
    if request.quota.is_stale(request.now):
        # Stale data cannot clear a limit either way; handled by the
        # authorization check, which will not reach PROVIDER_CONFIRMED.
        return None
    return f"other-limit-still-exhausted:{','.join(sorted(still_exhausted))}"


_CONDITIONS: tuple[Callable[[ResumeRequest], str | None], ...] = (
    _check_selected,
    _check_not_unsafe,
    _check_same_session,
    _check_same_process,
    _check_is_agent,
    _check_provider_matches,
    _check_recognised_prompt,
    _check_no_veto,
    _check_policy_allows_resume,
    _check_action_exists,
    _check_action_policy,
    _check_not_already_actioned,
    _check_attempts,
    _check_no_other_limit,
)


# -- authorization ---------------------------------------------------------


def _resume_at(request: ResumeRequest) -> datetime | None:
    """When the relevant limit is expected to clear, plus the grace period.

    Provider state is preferred over the reset time printed in the terminal, and
    the later of the two wins when both are known - a nominal reset that has
    passed is not proof that usage returned (vision section 24).
    """
    candidates = [
        moment
        for moment in (request.quota.next_reset, request.recognition.reset_at)
        if moment is not None
    ]
    if not candidates:
        return None
    return max(candidates) + timedelta(seconds=request.config.reset_grace)


def authorization_for(request: ResumeRequest) -> tuple[Authorization, datetime | None]:
    """Grade the evidence that usage is available again.

    Returns the grade and, when the answer is "not yet", the instant at which it
    is worth asking again.
    """
    quota = request.quota
    fresh = not quota.is_stale(request.now)
    action = request.recognition.action

    # Arming Claude's own wait is intentionally done while the provider says
    # the session limit is exhausted. It is not a claim that usage returned.
    if action is not None and action.kind is ActionKind.ARROW_DOWN_THEN_ENTER:
        if fresh and quota.availability is Availability.EXHAUSTED:
            return Authorization.PROVIDER_CONFIRMED, None
        return Authorization.NONE, None

    if fresh and quota.availability is Availability.EXHAUSTED:
        return Authorization.NONE, _resume_at(request)

    # The provider's own "usage limit has reset - press enter to continue" is a
    # first-hand statement that the window reopened, and outranks a clock.
    if request.recognition.state is SessionState.READY_TO_RESUME:
        return Authorization.PROVIDER_CONFIRMED, None

    if fresh and quota.availability is Availability.AVAILABLE:
        return Authorization.PROVIDER_CONFIRMED, None

    resume_at = _resume_at(request)
    if resume_at is None:
        # No provider state and no reset time: nothing at all says usage
        # returned, so there is nothing to wait for either.
        return Authorization.NONE, None
    if request.now >= resume_at:
        return Authorization.TIME_ONLY, None
    return Authorization.NONE, resume_at


def evaluate(request: ResumeRequest) -> Decision:
    """Run the whole gate.

    The conditions are checked in order and the first refusal wins, so the
    reason reported is the earliest thing that was wrong rather than an
    arbitrary one.
    """
    key = idempotency_key(request)
    authorization, retry_at = authorization_for(request)

    # Every refusal carries `retry_at` when one is known, including refusals
    # that never reach the authorization step. A session blocked by Claude has
    # nothing to type yet - the action only appears with the "press enter to
    # continue" affordance - but the loop still needs to know when to look
    # again, and polling every two seconds for four hours is not that.
    for condition in _CONDITIONS:
        reason = condition(request)
        if reason is not None:
            return Decision(allowed=False, reason=reason, retry_at=retry_at, idempotency_key=key)

    action = request.recognition.action

    if authorization is Authorization.NONE:
        return Decision(
            allowed=False,
            reason="usage-not-confirmed-available",
            action=action,
            authorization=authorization,
            retry_at=retry_at,
            idempotency_key=key,
        )

    mode = request.config.mode
    if mode is Mode.OBSERVE:
        return Decision(
            allowed=False,
            reason="observe-mode",
            action=action,
            authorization=authorization,
            idempotency_key=key,
        )

    if mode is Mode.AUTO and authorization is Authorization.TIME_ONLY:
        # DANGER 19: with no provider confirmation, auto mode fails closed and
        # the same situation merely asks in ask mode.
        return Decision(
            allowed=False,
            reason="auto-mode-requires-provider-confirmation",
            action=action,
            authorization=authorization,
            idempotency_key=key,
        )

    return Decision(
        allowed=True,
        reason="all-conditions-met",
        action=action,
        authorization=authorization,
        requires_confirmation=mode is Mode.ASK,
        idempotency_key=key,
    )
