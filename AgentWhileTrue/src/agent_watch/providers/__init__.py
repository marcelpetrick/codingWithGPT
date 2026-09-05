"""Provider adapters and the registry that maps a process class to one."""

from __future__ import annotations

from agent_watch.classify import ProcessClass
from agent_watch.providers.base import (
    ActionKind,
    PromptKind,
    PromptMatch,
    PromptPattern,
    ProviderAdapter,
    Recognition,
    ResumeAction,
)
from agent_watch.providers.claude import ClaudeAdapter
from agent_watch.providers.codex import CodexAdapter

CLAUDE = ClaudeAdapter()
CODEX = CodexAdapter()

_BY_CLASS: dict[ProcessClass, ProviderAdapter] = {
    ProcessClass.CLAUDE: CLAUDE,
    ProcessClass.CODEX: CODEX,
}

_BY_NAME: dict[str, ProviderAdapter] = {CLAUDE.name: CLAUDE, CODEX.name: CODEX}


def for_process_class(process_class: ProcessClass) -> ProviderAdapter | None:
    """Return the adapter for a classified process, or ``None``.

    ``None`` is the correct answer for every non-agent class and is what keeps
    an unrecognised process from ever reaching the policy gate.
    """
    return _BY_CLASS.get(process_class)


def by_name(name: str) -> ProviderAdapter | None:
    return _BY_NAME.get(name)


def all_adapters() -> tuple[ProviderAdapter, ...]:
    return (CLAUDE, CODEX)


__all__ = [
    "CLAUDE",
    "CODEX",
    "ActionKind",
    "ClaudeAdapter",
    "CodexAdapter",
    "PromptKind",
    "PromptMatch",
    "PromptPattern",
    "ProviderAdapter",
    "Recognition",
    "ResumeAction",
    "all_adapters",
    "by_name",
    "for_process_class",
]
