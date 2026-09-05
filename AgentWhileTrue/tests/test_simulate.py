"""The safety scenarios are assertions, not demonstrations.

Section 40 of the vision lists the situations that must be exercised; this test
fails the build if any of them stops holding.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from agent_watch import simulate
from agent_watch.cli import EXIT_ERROR, EXIT_OK, main


@pytest.mark.parametrize("name", sorted(simulate.SCENARIOS))
def test_every_scenario_holds(name: str, tmp_path: Path) -> None:
    result = simulate.run(name, tmp_path)
    assert result.passed, result.render()


def test_the_happy_path_actually_sends_something(tmp_path: Path) -> None:
    # A suite of scenarios that all pass by never typing would prove nothing.
    result = simulate.run("reset-and-resume", tmp_path)
    assert result.sent == [(simulate.SESSION, "\r")]


def test_every_other_scenario_stays_silent(tmp_path: Path) -> None:
    talkative = {"reset-and-resume", "duplicate-prompt"}
    for name in simulate.SCENARIOS:
        if name in talkative:
            continue
        assert simulate.run(name, tmp_path).sent == [], name


def test_scenarios_are_documented() -> None:
    for name, description in simulate.catalogue():
        assert description, name
        assert name in simulate.SCENARIOS


def test_cli_lists_scenarios() -> None:
    out = io.StringIO()
    assert main(["simulate"], stream=out) == EXIT_OK
    assert "agent-exited" in out.getvalue()


def test_cli_runs_one_scenario() -> None:
    out = io.StringIO()
    assert main(["simulate", "agent-exited"], stream=out) == EXIT_OK
    assert "result     PASS" in out.getvalue()
    assert "DANGER 2" in out.getvalue()


def test_cli_runs_them_all() -> None:
    out = io.StringIO()
    assert main(["simulate", "--all"], stream=out) == EXIT_OK
    assert out.getvalue().count("PASS") == len(simulate.SCENARIOS)


def test_cli_rejects_an_unknown_scenario() -> None:
    out = io.StringIO()
    assert main(["simulate", "no-such-thing"], stream=out) == EXIT_ERROR
