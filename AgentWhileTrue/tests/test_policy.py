"""Tests for the resume gate.

These are the most important tests in the project: each one pins a condition
from section 17 of the vision, or one of the numbered dangers, to a refusal
reason that a log reader can act on.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from agent_watch import providers
from agent_watch.classify import Classification, Confidence, ProcessClass
from agent_watch.config import Config, Mode, Policy
from agent_watch.policy import Authorization, ResumeRequest, evaluate, idempotency_key
from agent_watch.proc import ProcessIdentity
from agent_watch.providers import ActionKind
from agent_watch.quota import Availability, QuotaSnapshot, QuotaWindow
from agent_watch.terminal.base import SessionRef
from tests import screens

NOW = datetime(2026, 9, 5, 20, 30, tzinfo=UTC)
REF = SessionRef("konsole", "org.kde.konsole-4452", "/Sessions/1")
IDENTITY = ProcessIdentity(pid=15102, start_time=987654, tty="pts/3", exe="/opt/claude")
AGENT = Classification(ProcessClass.CLAUDE, Confidence.HIGH, ("comm=claude", "argv0=claude"))

QUOTA_AVAILABLE = QuotaSnapshot(
    provider="claude",
    availability=Availability.AVAILABLE,
    source="test",
    observed_at=NOW,
    windows=(QuotaWindow("session", 12.0, None),),
)
QUOTA_EXHAUSTED = QuotaSnapshot(
    provider="claude",
    availability=Availability.EXHAUSTED,
    source="test",
    observed_at=NOW,
    windows=(QuotaWindow("session", 100.0, NOW + timedelta(minutes=10)),),
)
QUOTA_UNKNOWN = QuotaSnapshot(provider="claude", availability=Availability.UNKNOWN, source="test")


def make_request(**overrides) -> ResumeRequest:
    """A request that is allowed by default, so each test breaks one thing."""
    base = {
        "now": NOW,
        "config": Config(mode=Mode.AUTO),
        "selected": True,
        "selected_ref": REF,
        "live_ref": REF,
        "selected_identity": IDENTITY,
        "live_identity": IDENTITY,
        "classification": AGENT,
        "recognition": providers.CLAUDE.recognise(screens.CLAUDE_READY_TO_RESUME, now=NOW),
        "quota": QUOTA_AVAILABLE,
    }
    return ResumeRequest(**{**base, **overrides})


def test_the_happy_path_is_allowed() -> None:
    decision = evaluate(make_request())
    assert decision.allowed
    assert decision.reason == "all-conditions-met"
    assert decision.action is not None
    assert decision.action.keystrokes() == "\r"
    assert decision.authorization is Authorization.PROVIDER_CONFIRMED


def test_unselected_session_is_refused() -> None:
    assert evaluate(make_request(selected=False)).reason == "session-not-selected-by-user"


def test_session_marked_unsafe_is_refused() -> None:
    assert evaluate(make_request(marked_unsafe=True)).reason == "session-marked-unsafe"


def test_a_different_konsole_session_is_refused() -> None:
    other = SessionRef("konsole", "org.kde.konsole-9999", "/Sessions/1")
    assert evaluate(make_request(live_ref=other)).reason == "konsole-session-changed"


def test_a_vanished_process_is_refused() -> None:
    assert evaluate(make_request(live_identity=None)).reason == "process-gone"


def test_pid_reuse_is_refused() -> None:
    # DANGER 1: same PID, different start time. Not the same process.
    recycled = replace(IDENTITY, start_time=IDENTITY.start_time + 1)
    assert evaluate(make_request(live_identity=recycled)).reason == "process-identity-changed"


def test_agent_replaced_by_a_shell_is_refused() -> None:
    # DANGER 2: codex exits, zsh takes the foreground, the old timer fires.
    shell = Classification(ProcessClass.SHELL, Confidence.HIGH, ("comm=zsh",), blocker="idle-shell")
    decision = evaluate(make_request(classification=shell))
    assert decision.reason == "not-automatable:idle-shell"


def test_low_confidence_classification_is_refused() -> None:
    weak = Classification(ProcessClass.CLAUDE, Confidence.LOW, ("exe-under-claude-versions",))
    assert evaluate(make_request(classification=weak)).reason.startswith("not-automatable:")


def test_recognizer_and_process_class_must_agree() -> None:
    codex_recognition = providers.CODEX.recognise(screens.CODEX_USAGE_LIMIT, now=NOW)
    assert evaluate(make_request(recognition=codex_recognition)).reason == "provider-mismatch"


def test_an_active_screen_has_no_blocking_prompt() -> None:
    active = providers.CLAUDE.recognise(screens.CLAUDE_ACTIVE, now=NOW)
    decision = evaluate(make_request(recognition=active))
    assert decision.reason.startswith("no-recognised-blocking-prompt")


def test_self_healing_banner_vetoes_the_action() -> None:
    healing = providers.CLAUDE.recognise(screens.CLAUDE_SELF_HEALING, now=NOW)
    assert evaluate(make_request(recognition=healing)).reason.startswith("provider-resumes-itself")


def test_spend_limit_is_never_automated() -> None:
    spend = providers.CLAUDE.recognise(screens.CLAUDE_SPEND_LIMIT, now=NOW)
    assert evaluate(make_request(recognition=spend)).reason.startswith("paid-action-required")


def test_model_downgrade_is_never_automated() -> None:
    downgrade = providers.CLAUDE.recognise(screens.CLAUDE_MODEL_DOWNGRADE, now=NOW)
    assert evaluate(make_request(recognition=downgrade)).reason.startswith("model-downgrade-offer")


def test_codex_resume_needs_its_own_opt_in() -> None:
    codex = Classification(ProcessClass.CODEX, Confidence.HIGH, ("comm=codex", "argv0=codex"))
    recognition = providers.CODEX.recognise(screens.CODEX_USAGE_LIMIT, now=NOW)
    request = make_request(
        classification=codex,
        recognition=recognition,
        quota=replace(QUOTA_AVAILABLE, provider="codex"),
    )
    assert evaluate(request).reason == "action-requires-policy:allow_codex_auto_resume"

    opted_in = replace(request.config, policy=Policy(allow_codex_auto_resume=True))
    allowed = evaluate(replace(request, config=opted_in))
    assert allowed.allowed
    assert allowed.action is not None
    assert allowed.action.keystrokes() == "continue\r"


def test_disabling_resume_policy_refuses_everything() -> None:
    config = Config(mode=Mode.AUTO, policy=Policy(resume_after_reset=False))
    assert evaluate(make_request(config=config)).reason == "policy-disallows-resume"


def test_the_same_prompt_is_only_actioned_once() -> None:
    # DANGER 17: one logical prompt, one possible action.
    request = make_request()
    key = idempotency_key(request)
    repeated = make_request(actioned_fingerprints=frozenset({key}))
    assert evaluate(repeated).reason == "already-actioned"


def test_a_restarted_agent_gets_a_new_idempotency_key() -> None:
    # DANGER 18: same tab, same project, new process is a new identity.
    first = make_request()
    restarted = make_request(
        selected_identity=replace(IDENTITY, pid=20000, start_time=111),
        live_identity=replace(IDENTITY, pid=20000, start_time=111),
    )
    assert idempotency_key(first) != idempotency_key(restarted)


def test_attempts_are_capped() -> None:
    assert evaluate(make_request(attempts=3)).reason == "max-resume-attempts-reached"


def test_a_still_exhausted_weekly_limit_blocks_a_five_hour_reset() -> None:
    # Vision section 25.
    quota = QuotaSnapshot(
        provider="claude",
        availability=Availability.EXHAUSTED,
        source="test",
        observed_at=NOW,
        windows=(
            QuotaWindow("session", 3.0, None),
            QuotaWindow("weekly", 100.0, NOW + timedelta(days=2)),
        ),
    )
    decision = evaluate(make_request(quota=quota))
    assert decision.reason == "other-limit-still-exhausted:weekly"


def test_observe_mode_never_acts() -> None:
    config = Config(mode=Mode.OBSERVE)
    decision = evaluate(make_request(config=config))
    assert not decision.allowed
    assert decision.reason == "observe-mode"
    # It still worked out what it *would* do, which is what observe mode is for.
    assert decision.action is not None


def test_ask_mode_requires_confirmation() -> None:
    decision = evaluate(make_request(config=Config(mode=Mode.ASK)))
    assert decision.allowed
    assert decision.requires_confirmation


def _blocked_with_reset():
    return providers.CLAUDE.recognise(
        ["You've hit your session limit · resets in 10m", "❯ "], now=NOW
    )


def test_a_blocked_claude_screen_offers_no_action_yet() -> None:
    # There is genuinely nothing to type while Claude is blocked; the action
    # only exists once the "press enter to continue" affordance appears.
    decision = evaluate(make_request(recognition=_blocked_with_reset()))
    assert not decision.allowed
    assert decision.reason == "no-unambiguous-action-for-prompt"


def test_claude_wait_menu_can_be_armed_only_with_fresh_exhausted_quota() -> None:
    menu = providers.CLAUDE.recognise(screens.CLAUDE_LIMIT_MENU, now=NOW)
    allowed = evaluate(make_request(recognition=menu, quota=QUOTA_EXHAUSTED))
    assert allowed.allowed
    assert allowed.action is not None
    assert allowed.action.kind is ActionKind.ARROW_DOWN_THEN_ENTER

    unknown = evaluate(make_request(recognition=menu, quota=QUOTA_UNKNOWN))
    assert not unknown.allowed
    assert unknown.reason == "usage-not-confirmed-available"

    disabled = Config(mode=Mode.AUTO, policy=Policy(allow_claude_auto_wait=False))
    refused = evaluate(make_request(config=disabled, recognition=menu, quota=QUOTA_EXHAUSTED))
    assert not refused.allowed
    assert refused.reason == "action-requires-policy:allow_claude_auto_wait"


def test_a_refusal_still_says_when_to_look_again() -> None:
    # Without this the loop would poll every two seconds for four hours.
    decision = evaluate(make_request(recognition=_blocked_with_reset(), quota=QUOTA_UNKNOWN))
    assert not decision.allowed
    assert decision.retry_at is not None
    assert decision.retry_at > NOW


def test_grace_period_is_added_to_the_reset_time() -> None:
    config = Config(mode=Mode.ASK, reset_grace=300.0)
    decision = evaluate(
        make_request(config=config, recognition=_blocked_with_reset(), quota=QUOTA_UNKNOWN)
    )
    assert decision.retry_at == NOW + timedelta(minutes=10) + timedelta(seconds=300)


def _codex_request(**overrides):
    """A Codex request with the opt-in granted, so quota logic is reachable."""
    codex = Classification(ProcessClass.CODEX, Confidence.HIGH, ("comm=codex", "argv0=codex"))
    return make_request(
        classification=codex,
        config=Config(mode=Mode.AUTO, policy=Policy(allow_codex_auto_resume=True)),
        **overrides,
    )


def test_unknown_quota_never_means_available() -> None:
    # DANGER 19, on a blocked screen with no reset time to fall back on.
    blocked = providers.CODEX.recognise(["You've hit your usage limit.", "> "], now=NOW)
    decision = evaluate(_codex_request(recognition=blocked, quota=QUOTA_UNKNOWN))
    assert not decision.allowed
    assert decision.reason == "usage-not-confirmed-available"
    assert decision.authorization is Authorization.NONE


def test_time_only_authorization_is_refused_in_auto_but_offered_in_ask() -> None:
    # DANGER 19: an unknown provider state waits, asks, or fails closed
    # depending on the configured mode.
    past_reset = providers.CODEX.recognise(
        ["You've hit your usage limit. Try again at 8:10 PM.", "> "], now=NOW - timedelta(days=1)
    )
    request = _codex_request(recognition=past_reset, quota=QUOTA_UNKNOWN)
    auto = evaluate(request)
    assert not auto.allowed
    assert auto.reason == "auto-mode-requires-provider-confirmation"
    assert auto.authorization is Authorization.TIME_ONLY

    asking = replace(request.config, mode=Mode.ASK, policy=Policy(allow_codex_auto_resume=True))
    ask = evaluate(replace(request, config=asking))
    assert ask.allowed
    assert ask.requires_confirmation


def test_a_fresh_exhausted_quota_outranks_the_ready_prompt() -> None:
    # The screen says the limit reset, the provider says it has not. Believe the
    # provider and wait.
    decision = evaluate(make_request(quota=QUOTA_EXHAUSTED))
    assert not decision.allowed
    assert decision.reason.startswith("other-limit-still-exhausted")


def test_stale_quota_does_not_authorise_auto_mode() -> None:
    stale = replace(QUOTA_AVAILABLE, observed_at=NOW - timedelta(hours=3))
    decision = evaluate(make_request(quota=stale))
    # The ready-to-resume prompt still carries it, because that is the provider
    # speaking first-hand rather than a cached number.
    assert decision.allowed
    assert decision.authorization is Authorization.PROVIDER_CONFIRMED


@pytest.mark.parametrize("mode", list(Mode))
def test_every_mode_refuses_a_shell(mode: Mode) -> None:
    shell = Classification(ProcessClass.SHELL, Confidence.HIGH, ("comm=zsh",), blocker="idle-shell")
    decision = evaluate(make_request(config=Config(mode=mode), classification=shell))
    assert not decision.allowed
