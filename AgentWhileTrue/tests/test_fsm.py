"""End-to-end tests of the supervisor loop, driven entirely by fakes."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_watch.config import Config, Mode, Policy
from agent_watch.quota import Availability
from agent_watch.states import ActionState, SessionState
from tests import harness as harness_module
from tests import screens

SESSION = "/Sessions/1"
PID = 15102


def _claude_session(tmp_path: Path, *, mode=Mode.AUTO, screen=None, confirm=None, config=None):
    kit = harness_module.build(tmp_path, mode=mode, confirm=confirm, config=config)
    info = kit.inspector.add_claude(PID)
    ref = kit.terminal.add(
        SESSION,
        shell_pid=100,
        foreground_pid=PID,
        screen=list(screen or screens.CLAUDE_READY_TO_RESUME),
        title="project : claude",
    )
    kit.supervisor.select(ref, info.identity, "claude", "project : claude")
    return kit, ref


def test_a_ready_prompt_is_resumed_with_a_single_enter(tmp_path: Path) -> None:
    kit, _ = _claude_session(tmp_path)
    decisions = kit.supervisor.tick()
    assert decisions[0].allowed
    assert kit.sent == [(SESSION, "\r")]


def test_claude_limit_menu_arms_provider_auto_wait_and_verifies(tmp_path: Path) -> None:
    kit, _ = _claude_session(tmp_path, screen=list(screens.CLAUDE_LIMIT_MENU))
    kit.quota["claude"].availability = Availability.EXHAUSTED

    decisions = kit.supervisor.tick()
    assert decisions[0].allowed
    assert kit.sent == [(SESSION, "\x1b[B\r")]

    kit.terminal.set_screen(SESSION, list(screens.CLAUDE_SELF_HEALING))
    kit.clock.advance(5)
    harness_module.refresh_quota(kit)
    verified = kit.supervisor.tick()
    assert verified[0].reason == "verify:armed-provider-wait"
    session = kit.supervisor.sessions[kit.terminal.ref(SESSION).key()]
    assert session.state is SessionState.WAITING_FOR_RESET


def test_an_outstanding_action_is_not_repeated_while_it_is_unverified(tmp_path: Path) -> None:
    # DANGER 17: one logical prompt has one action outstanding at a time,
    # however many times the same screen is scanned.
    kit, _ = _claude_session(tmp_path)
    kit.supervisor.tick()
    for _ in range(5):
        kit.clock.advance(1)  # still inside the verification window
        kit.supervisor.tick()
    assert kit.sent == [(SESSION, "\r")]


def test_a_verified_resume_is_never_re_sent(tmp_path: Path) -> None:
    kit, _ = _claude_session(tmp_path)
    kit.supervisor.tick()
    kit.terminal.set_screen(SESSION, list(screens.CLAUDE_ACTIVE))
    for _ in range(5):
        kit.clock.advance(10)
        harness_module.refresh_quota(kit)
        kit.supervisor.tick()
    assert kit.sent == [(SESSION, "\r")]


def test_observe_mode_never_sends_anything(tmp_path: Path) -> None:
    kit, _ = _claude_session(tmp_path, mode=Mode.OBSERVE)
    decisions = kit.supervisor.tick()
    assert not decisions[0].allowed
    assert decisions[0].reason == "observe-mode"
    # Observe mode still worked out what it would have done.
    assert decisions[0].action is not None
    assert kit.sent == []


def test_ask_mode_sends_only_after_confirmation(tmp_path: Path) -> None:
    declined, _ = _claude_session(tmp_path / "no", mode=Mode.ASK, confirm=False)
    declined.supervisor.tick()
    assert declined.sent == []

    accepted, _ = _claude_session(tmp_path / "yes", mode=Mode.ASK, confirm=True)
    accepted.supervisor.tick()
    assert accepted.sent == [(SESSION, "\r")]


def test_ask_mode_without_a_way_to_ask_refuses(tmp_path: Path) -> None:
    kit, _ = _claude_session(tmp_path, mode=Mode.ASK, confirm=None)
    kit.supervisor.tick()
    assert kit.sent == []


def test_the_agent_exiting_between_deciding_and_typing_cancels_the_send(tmp_path: Path) -> None:
    # DANGER 2: codex/claude exits, zsh takes the foreground, the timer fires.
    # The swap happens after the first screen read, i.e. after the decision was
    # made but before the revalidation that guards the keystroke.
    kit, _ = _claude_session(tmp_path)
    reads = {"n": 0}

    def swap_after_first_read(session_id: str) -> None:
        reads["n"] += 1
        if reads["n"] == 1:
            shell = kit.inspector.add_shell(PID + 1)
            kit.terminal.set_foreground(session_id, shell.identity.pid)
            kit.terminal.set_screen(session_id, ["user@host ~/project %"])

    kit.terminal.after_read = swap_after_first_read
    decisions = kit.supervisor.tick()
    assert not decisions[0].allowed
    assert decisions[0].reason.startswith("revalidation-failed")
    assert kit.sent == []


def test_a_recycled_pid_is_not_the_same_process(tmp_path: Path) -> None:
    # DANGER 1: same PID, different start time.
    kit, _ = _claude_session(tmp_path)
    kit.inspector.add_claude(PID, start_time=999999)
    decisions = kit.supervisor.tick()
    assert decisions[0].reason == "process-identity-changed"
    assert kit.sent == []


def test_a_closed_tab_produces_no_input(tmp_path: Path) -> None:
    kit, _ = _claude_session(tmp_path)
    kit.terminal.close(SESSION)
    decisions = kit.supervisor.tick()
    assert not decisions[0].allowed
    assert kit.sent == []


def test_one_broken_session_does_not_stop_the_others(tmp_path: Path) -> None:
    kit, _ = _claude_session(tmp_path)
    other_info = kit.inspector.add_claude(20000, start_time=444, tty="pts/9")
    other_ref = kit.terminal.add(
        "/Sessions/2",
        shell_pid=200,
        foreground_pid=20000,
        screen=list(screens.CLAUDE_READY_TO_RESUME),
    )
    kit.supervisor.select(other_ref, other_info.identity, "claude", "other")
    kit.terminal.close(SESSION)

    kit.supervisor.tick()
    assert kit.sent == [("/Sessions/2", "\r")]


def test_verification_settles_a_successful_resume(tmp_path: Path) -> None:
    kit, _ = _claude_session(tmp_path)
    kit.supervisor.tick()
    key = kit.supervisor.sessions[kit.terminal.ref(SESSION).key()].pending_key

    kit.terminal.set_screen(SESSION, list(screens.CLAUDE_ACTIVE))
    kit.clock.advance(10)
    harness_module.refresh_quota(kit)
    decisions = kit.supervisor.tick()

    assert decisions[0].reason == "resume-verified"
    assert kit.supervisor.store.records[key].state is ActionState.VERIFIED


def test_a_failed_resume_backs_off_instead_of_hammering(tmp_path: Path) -> None:
    kit, _ = _claude_session(tmp_path)
    kit.supervisor.tick()
    assert len(kit.sent) == 1

    # The prompt is still there after the keystroke.
    kit.clock.advance(10)
    harness_module.refresh_quota(kit)
    decisions = kit.supervisor.tick()
    assert decisions[0].reason == "verify:still-blocked"
    assert decisions[0].retry_at is not None

    # And the next tick respects the back-off rather than resending.
    kit.clock.advance(1)
    kit.supervisor.tick()
    assert len(kit.sent) == 1


def test_a_changing_screen_cannot_mint_an_unlimited_attempt_budget(tmp_path: Path) -> None:
    # The store counts attempts per prompt fingerprint, so a screen that keeps
    # changing would otherwise get a fresh budget on every tick. The
    # per-session counter is what actually bounds this.
    kit, _ = _claude_session(tmp_path)
    session = kit.supervisor.sessions[kit.terminal.ref(SESSION).key()]
    for round_number in range(8):
        kit.supervisor.tick()
        kit.clock.advance(120)
        harness_module.refresh_quota(kit)
        kit.terminal.set_screen(
            SESSION, [*screens.CLAUDE_READY_TO_RESUME, f"  build step {round_number}"]
        )
        session.verify_after = None
        session.next_check_at = None
    assert len(kit.sent) <= Config().max_resume_attempts


def test_a_suspend_across_the_reset_does_not_replay_a_stale_action(tmp_path: Path) -> None:
    # DANGER 9: reset at 02:00, sleep at 01:30, wake at 08:00.
    kit, _ = _claude_session(tmp_path, screen=list(screens.CLAUDE_SESSION_LIMIT))
    kit.supervisor.tick()
    assert kit.sent == []

    kit.clock.suspend(6 * 3600)
    harness_module.refresh_quota(kit)
    # On waking, the agent is gone and a shell has the foreground.
    shell = kit.inspector.add_shell(PID + 5)
    kit.terminal.set_foreground(SESSION, shell.identity.pid)
    kit.terminal.set_screen(SESSION, ["user@host ~/project %"])

    kit.supervisor.tick()
    assert kit.sent == []


def test_a_time_jump_discards_pending_schedules(tmp_path: Path) -> None:
    kit, _ = _claude_session(tmp_path, screen=list(screens.CLAUDE_SESSION_LIMIT))
    kit.supervisor.tick()
    session = kit.supervisor.sessions[kit.terminal.ref(SESSION).key()]
    session.next_check_at = kit.clock.wall
    kit.clock.suspend(3600)
    kit.supervisor.tick()
    assert session.next_check_at is None or session.next_check_at != kit.clock.wall


def test_a_wedged_terminal_marks_the_action_failed(tmp_path: Path) -> None:
    kit, _ = _claude_session(tmp_path)
    kit.terminal.send_fails = True
    decisions = kit.supervisor.tick()
    assert decisions[0].reason == "send-failed"
    session = kit.supervisor.sessions[kit.terminal.ref(SESSION).key()]
    assert kit.supervisor.store.records[session.pending_key].state is ActionState.FAILED


def test_codex_is_not_resumed_without_the_opt_in(tmp_path: Path) -> None:
    kit = harness_module.build(tmp_path, mode=Mode.AUTO)
    info = kit.inspector.add_codex(30000)
    ref = kit.terminal.add(
        "/Sessions/7",
        shell_pid=300,
        foreground_pid=30000,
        screen=list(screens.CODEX_USAGE_LIMIT),
    )
    kit.supervisor.select(ref, info.identity, "codex", "codex")
    decisions = kit.supervisor.tick()
    assert decisions[0].reason == "action-requires-policy:allow_codex_auto_resume"
    assert kit.sent == []


def test_codex_is_resumed_once_the_user_opts_in(tmp_path: Path) -> None:
    config = Config(mode=Mode.AUTO, policy=Policy(allow_codex_auto_resume=True))
    kit = harness_module.build(tmp_path, config=config)
    info = kit.inspector.add_codex(30000)
    ref = kit.terminal.add(
        "/Sessions/7",
        shell_pid=300,
        foreground_pid=30000,
        screen=list(screens.CODEX_USAGE_LIMIT),
    )
    kit.supervisor.select(ref, info.identity, "codex", "codex")
    kit.supervisor.tick()
    assert kit.sent == [("/Sessions/7", "continue\r")]


def test_prune_removes_a_selection_whose_tab_is_gone(tmp_path: Path) -> None:
    # DANGER 20: a selection must not survive its tab and transfer to a new one.
    kit, _ = _claude_session(tmp_path)
    kit.terminal.close(SESSION)
    kit.supervisor.prune_and_rebind()
    assert kit.supervisor.sessions == {}


def test_marking_a_session_unsafe_stops_it(tmp_path: Path) -> None:
    kit, ref = _claude_session(tmp_path)
    kit.supervisor.mark_unsafe(ref.key(), "manual")
    decisions = kit.supervisor.tick()
    assert decisions[0].reason == "session-marked-unsafe"
    assert kit.sent == []
    assert kit.supervisor.sessions[ref.key()].state is SessionState.UNSAFE


@pytest.mark.parametrize("screen_name", ["CLAUDE_SELF_HEALING", "CLAUDE_SPEND_LIMIT"])
def test_vetoed_screens_are_never_actioned(tmp_path: Path, screen_name: str) -> None:
    kit, _ = _claude_session(tmp_path, screen=list(getattr(screens, screen_name)))
    kit.supervisor.tick()
    assert kit.sent == []


def test_the_event_log_records_the_send_without_the_screen(tmp_path: Path) -> None:
    kit, _ = _claude_session(tmp_path)
    kit.supervisor.tick()
    written = (tmp_path / "agent-watch.log").read_text()
    assert "event=resume_sent" in written
    assert "press enter to continue" not in written
    assert "session limit" not in written
