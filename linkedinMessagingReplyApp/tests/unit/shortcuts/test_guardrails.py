# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from linkedin_reply_assistant.shortcuts.base import Binding, DisabledShortcuts, ShortcutStatus
from linkedin_reply_assistant.shortcuts.guardrails import check_trigger, normalize


def test_normalize() -> None:
    assert normalize("alt + ctrl + l") == "CTRL+ALT+L"
    assert normalize("Super+Shift+K") == "SHIFT+LOGO+K"
    assert normalize("control+escape") == "CTRL+ESC"
    assert normalize("") == ""


@pytest.mark.parametrize(
    ("trigger", "reason"),
    [
        ("CTRL", "needs a key"),
        ("", "needs a key"),
        ("CTRL+A+B", "only one key"),
        ("L", "needs Ctrl, Alt or Super"),
        ("SHIFT+L", "needs Ctrl, Alt or Super"),
        ("ALT+F4", "reserved"),
        ("CTRL+ALT+F3", "virtual terminal"),
        ("CTRL+R", "inside the application"),
        ("Escape+ctrl", None),
        ("CTRL+ALT+L", None),
        ("CTRL+ALT+FOO", None),
        ("LOGO+SHIFT+F2", None),
    ],
)
def test_check_trigger(trigger: str, reason: str | None) -> None:
    result = check_trigger(trigger)
    if reason is None:
        assert result is None
    else:
        assert result is not None and reason in result


def test_disabled_service() -> None:
    service = DisabledShortcuts()
    status = service.start(lambda s: None)
    assert not status.available and "remains available" in status.message
    assert not service.bind("a", "b", "CTRL+ALT+L").active
    assert service.configure() is False
    service.close()


def test_status_active() -> None:
    assert ShortcutStatus(True, Binding("a", "b", "Ctrl+L"), "").active
    assert not ShortcutStatus(True, Binding("a", "b", ""), "").active
    assert not ShortcutStatus(True, None, "").active
