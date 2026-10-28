# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reject obviously unsuitable triggers before asking the portal (§7.3).

This is a guardrail, not a system-wide conflict detector: the compositor stays the authority.
"""

MODIFIERS = ("CTRL", "ALT", "SHIFT", "LOGO")
ALIASES = {"CONTROL": "CTRL", "SUPER": "LOGO", "META": "LOGO", "WIN": "LOGO", "ESCAPE": "ESC"}
# In-application shortcuts (VISION §17.2). A global trigger must not shadow them.
LOCAL_SHORTCUTS = ("CTRL+R", "ESC", "CTRL+D", "CTRL+E", "CTRL+Q")
RESERVED = {"ALT+F4", "ALT+TAB", "CTRL+ALT+DELETE", "CTRL+ALT+BACKSPACE", "LOGO+L"}


def normalize(trigger: str) -> str:
    """Upper-case, resolve aliases, modifiers first: 'alt+ctrl+l' -> 'CTRL+ALT+L'."""
    parts = [p.strip().upper() for p in trigger.replace(" ", "").split("+") if p.strip()]
    parts = [ALIASES.get(p, p) for p in parts]
    modifiers = [m for m in MODIFIERS if m in parts]
    keys = [p for p in parts if p not in MODIFIERS]
    return "+".join(modifiers + keys)


def check_trigger(trigger: str, local: tuple[str, ...] = LOCAL_SHORTCUTS) -> str | None:
    """Return a reason why the trigger is unsuitable, or None if it may be proposed."""
    normalized = normalize(trigger)
    parts = normalized.split("+") if normalized else []
    keys = [p for p in parts if p not in MODIFIERS]
    modifiers = [p for p in parts if p in MODIFIERS]
    if not keys:
        return "a shortcut needs a key, not only modifiers"
    if len(keys) > 1:
        return "a shortcut can have only one key"
    if not modifiers or modifiers == ["SHIFT"]:
        return "a global shortcut needs Ctrl, Alt or Super"
    if normalized in RESERVED:
        return f"{normalized} is reserved by the desktop"
    if modifiers == ["CTRL", "ALT"] and keys[0].startswith("F") and keys[0][1:].isdigit():
        return "Ctrl+Alt+F-keys switch the virtual terminal"
    if normalized in {normalize(s) for s in local}:
        return f"{normalized} is used inside the application"
    return None
