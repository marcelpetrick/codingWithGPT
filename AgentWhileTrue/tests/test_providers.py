"""Recognizer tests, driven by verbatim screens from the real CLIs."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from agent_watch import providers
from agent_watch.classify import ProcessClass
from agent_watch.providers import ActionKind, PromptKind
from agent_watch.states import SessionState
from tests import screens

BERLIN = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 9, 5, 19, 31, tzinfo=BERLIN)


def test_claude_session_limit_is_blocked_with_a_reset_time() -> None:
    result = providers.CLAUDE.recognise(screens.CLAUDE_SESSION_LIMIT, now=NOW)
    assert result.state is SessionState.LIMIT_BLOCKED
    assert "claude/limit-session" in result.matched_ids
    assert result.reset_at == datetime(2026, 9, 5, 20, 10, tzinfo=BERLIN)
    assert result.blocked_scopes == {"session"}


def test_claude_session_limit_screen_also_flags_the_paid_offer() -> None:
    # The same screen advertises /upgrade and /usage-credits. That must register
    # as a veto so no automation runs while a paid path is on offer.
    result = providers.CLAUDE.recognise(screens.CLAUDE_SESSION_LIMIT, now=NOW)
    assert any(veto.startswith("paid-action-required") for veto in result.vetoes)


def test_real_claude_limit_menu_is_blocked_but_never_selected() -> None:
    """The menu in media/claude_out_of_quota.png is evidence, not an action affordance."""
    result = providers.CLAUDE.recognise(screens.CLAUDE_LIMIT_MENU, now=NOW)
    assert result.state is SessionState.LIMIT_BLOCKED
    assert result.reset_at == datetime(2026, 9, 6, 3, 20, tzinfo=BERLIN)
    assert result.action is None
    assert "claude/limit-session" in result.matched_ids
    assert "claude/upgrade-plan-offer" in result.matched_ids
    assert "claude/self-healing" not in result.matched_ids
    assert any(veto.startswith("paid-action-required") for veto in result.vetoes)


def test_claude_ready_to_resume_proposes_a_bare_enter() -> None:
    result = providers.CLAUDE.recognise(screens.CLAUDE_READY_TO_RESUME, now=NOW)
    assert result.state is SessionState.READY_TO_RESUME
    action = result.action
    assert action is not None
    assert action.kind is ActionKind.ENTER
    assert action.keystrokes() == "\r"
    # The literal word "continue" is never typed at this prompt.
    assert "continue" not in action.keystrokes()


def test_claude_self_healing_screen_vetoes_action() -> None:
    result = providers.CLAUDE.recognise(screens.CLAUDE_SELF_HEALING, now=NOW)
    assert any(veto.startswith("provider-resumes-itself") for veto in result.vetoes)


def test_claude_weekly_limit_is_a_separate_scope() -> None:
    result = providers.CLAUDE.recognise(screens.CLAUDE_WEEKLY_LIMIT, now=NOW)
    assert result.blocked_scopes == {"weekly"}
    assert result.reset_at is not None
    assert result.reset_at.weekday() == 0  # Monday


def test_claude_will_not_self_resume_is_the_case_worth_supervising() -> None:
    result = providers.CLAUDE.recognise(screens.CLAUDE_WILL_NOT_SELF_RESUME, now=NOW)
    kinds = {match.pattern.kind for match in result.matches}
    assert PromptKind.WILL_NOT_SELF_RESUME in kinds
    assert not any(veto.startswith("provider-resumes-itself") for veto in result.vetoes)


def test_claude_spend_limit_is_never_actionable() -> None:
    result = providers.CLAUDE.recognise(screens.CLAUDE_SPEND_LIMIT, now=NOW)
    assert any(veto.startswith("paid-action-required") for veto in result.vetoes)
    assert result.action is None


def test_claude_model_downgrade_offer_is_vetoed() -> None:
    result = providers.CLAUDE.recognise(screens.CLAUDE_MODEL_DOWNGRADE, now=NOW)
    assert any(veto.startswith("model-downgrade-offer") for veto in result.vetoes)


def test_claude_active_screen_proposes_nothing() -> None:
    result = providers.CLAUDE.recognise(screens.CLAUDE_ACTIVE, now=NOW)
    assert result.state is SessionState.ACTIVE
    assert result.action is None
    assert result.matches == ()


def test_scrolled_away_banner_cannot_trigger_anything() -> None:
    stale = screens.scrolled_away(screens.CLAUDE_READY_TO_RESUME)
    result = providers.CLAUDE.recognise(stale, now=NOW)
    assert result.state is SessionState.ACTIVE
    assert result.action is None


def test_codex_usage_limit_carries_the_reset_time() -> None:
    result = providers.CODEX.recognise(screens.CODEX_USAGE_LIMIT, now=NOW)
    assert result.state is SessionState.LIMIT_BLOCKED
    assert result.reset_at == datetime(2026, 9, 5, 20, 10, tzinfo=BERLIN)


def test_codex_resume_action_is_typing_and_needs_an_opt_in() -> None:
    result = providers.CODEX.recognise(screens.CODEX_USAGE_LIMIT, now=NOW)
    action = result.action
    assert action is not None
    assert action.kind is ActionKind.TEXT_THEN_ENTER
    assert action.keystrokes() == "continue\r"
    assert action.requires_policy == "allow_codex_auto_resume"


def test_codex_warning_is_not_a_block() -> None:
    result = providers.CODEX.recognise(screens.CODEX_APPROACHING, now=NOW)
    assert result.state is SessionState.LIMIT_WARNING


def test_codex_out_of_credits_is_vetoed() -> None:
    result = providers.CODEX.recognise(screens.CODEX_OUT_OF_CREDITS, now=NOW)
    assert any(veto.startswith("paid-action-required") for veto in result.vetoes)


def test_codex_model_downgrade_is_vetoed() -> None:
    result = providers.CODEX.recognise(screens.CODEX_MODEL_DOWNGRADE, now=NOW)
    assert any(veto.startswith("model-downgrade-offer") for veto in result.vetoes)


def test_codex_reset_credit_offer_is_vetoed() -> None:
    result = providers.CODEX.recognise(screens.CODEX_RESET_CREDIT, now=NOW)
    assert any(veto.startswith("paid-action-required") for veto in result.vetoes)


def test_codex_active_screen_proposes_nothing() -> None:
    result = providers.CODEX.recognise(screens.CODEX_ACTIVE, now=NOW)
    assert result.state is SessionState.ACTIVE
    assert result.action is None


def test_recognition_never_carries_the_whole_screen() -> None:
    result = providers.CLAUDE.recognise(screens.CLAUDE_SESSION_LIMIT, now=NOW)
    assert len(result.screen_fingerprint) == 12
    # Only the single matched line is retained, for reset parsing.
    for match in result.matches:
        assert match.line in screens.CLAUDE_SESSION_LIMIT


def test_registry_maps_only_agent_classes() -> None:
    assert providers.for_process_class(ProcessClass.CLAUDE) is providers.CLAUDE
    assert providers.for_process_class(ProcessClass.CODEX) is providers.CODEX
    for other in (ProcessClass.SHELL, ProcessClass.SSH, ProcessClass.UNKNOWN):
        assert providers.for_process_class(other) is None


def test_latest_reset_wins_when_two_windows_are_blocked() -> None:
    both = [*screens.CLAUDE_SESSION_LIMIT, *screens.CLAUDE_WEEKLY_LIMIT]
    result = providers.CLAUDE.recognise(both, now=NOW)
    assert result.blocked_scopes == {"session", "weekly"}
    assert result.reset_at is not None
    assert result.reset_at > NOW + timedelta(hours=1)


@pytest.mark.parametrize("adapter", providers.all_adapters())
def test_every_pattern_declares_what_it_was_verified_against(adapter) -> None:
    for pattern in adapter.patterns:
        assert pattern.verified_against, pattern.id
        assert pattern.id.startswith(f"{adapter.name}/")


def test_a_soft_wrapped_provider_sentence_still_matches() -> None:
    # A narrow terminal wraps one provider sentence across two screen lines.
    # Missing that would mean missing exactly the prompts that matter.
    wrapped = [
        "● Usage limit reached · resets in 30h",
        "  the usage limit now resets more than 24 hours out, so this task will",
        "  not resume on its own",
        "❯ ",
    ]
    result = providers.CLAUDE.recognise(wrapped, now=NOW)
    assert "claude/will-not-self-resume" in result.matched_ids


def test_a_reset_time_pushed_onto_a_wrapped_line_is_still_parsed() -> None:
    wrapped = [
        "  ⎿  You've hit your session limit ·",
        "     resets 8:10pm (Europe/Berlin)",
        "❯ ",
    ]
    result = providers.CLAUDE.recognise(wrapped, now=NOW)
    assert result.reset_at == datetime(2026, 9, 5, 20, 10, tzinfo=BERLIN)
