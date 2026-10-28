# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Load the YAML configuration.

A file in the user directory (~/.config/linkedin-reply-assistant/) replaces the shipped
default of the same name as a whole. Prompts follow the same rule per file. Every value is
validated here, so the rest of the application can trust the dataclasses.
"""

import os
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

APP_DIR_NAME = "linkedin-reply-assistant"
EXTRACTION_MODES = ("ocr", "vision", "hybrid")
CATEGORIES = (
    "friendly_connection",
    "congratulations_or_support",
    "generic_networking",
    "substantive_professional",
    "sales_outreach",
    "lead_generation",
    "meeting_request",
    "recruiting",
    "event_invitation",
    "partnership_request",
    "unknown_manual_review",
)
UNKNOWN_CATEGORY = "unknown_manual_review"


class ConfigError(ValueError):
    """A configuration file is missing, unreadable or invalid."""


def user_config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_DIR_NAME


@dataclass(frozen=True)
class HotkeyConfig:
    shortcut_id: str
    description: str
    preferred_trigger: str


@dataclass(frozen=True)
class ExtractionConfig:
    mode: str
    ocr_languages: str
    min_confidence: float
    min_characters: int


@dataclass(frozen=True)
class LanguageConfig:
    policy: str
    fixed: str
    supported: tuple[str, ...]


@dataclass(frozen=True)
class AppConfig:
    always_on_top: bool
    notify_on_draft: bool
    hotkey: HotkeyConfig
    extraction: ExtractionConfig
    language: LanguageConfig
    save_debug_captures: bool
    log_message_text: bool


@dataclass(frozen=True)
class BackendConfig:
    name: str
    label: str
    url: str
    priority: int
    connect_timeout_ms: int
    request_timeout_s: float
    reply_models: tuple[str, ...]
    vision_models: tuple[str, ...]

    @property
    def scheme(self) -> str:
        return urlparse(self.url).scheme


@dataclass(frozen=True)
class BackendsConfig:
    health_cache_seconds: float
    backends: tuple[BackendConfig, ...]


@dataclass(frozen=True)
class CategoryPolicy:
    policy: str
    prompt: str
    max_words: int


@dataclass(frozen=True)
class ClassificationRule:
    id: str
    category: str
    keywords: tuple[str, ...]
    min_hits: int


@dataclass(frozen=True)
class ReplyRules:
    style: tuple[str, ...]
    categories: dict[str, CategoryPolicy]
    rules: tuple[ClassificationRule, ...]


@dataclass(frozen=True)
class UserProfile:
    name: str
    sign_off: str
    sign_off_de: str
    allowed_facts: tuple[str, ...]
    mention_facts_in: tuple[str, ...]
    recruiting_preference: str


@dataclass(frozen=True)
class Config:
    app: AppConfig
    backends: BackendsConfig
    reply_rules: ReplyRules
    user_profile: UserProfile
    prompts: dict[str, str] = field(default_factory=dict)


def _defaults_dir() -> Path:
    return Path(str(resources.files("linkedin_reply_assistant") / "defaults"))


def _read_text(name: str, user_dir: Path) -> str:
    for candidate in (user_dir / name, _defaults_dir() / name):
        if candidate.is_file():
            try:
                return candidate.read_text(encoding="utf-8")
            except OSError as exc:  # pragma: no cover - permission errors are platform specific
                raise ConfigError(f"{candidate}: {exc}") from exc
    raise ConfigError(f"configuration file not found: {name}")


def _read_yaml(name: str, user_dir: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(_read_text(name, user_dir))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{name}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{name}: top level must be a mapping")
    return data


def _get(data: dict[str, Any], key: str, kind: type, where: str) -> Any:
    if key not in data:
        raise ConfigError(f"{where}: missing key '{key}'")
    value = data[key]
    if kind is float and isinstance(value, int) and not isinstance(value, bool):
        value = float(value)
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise ConfigError(f"{where}: '{key}' must be {kind.__name__}")
    return value


def _str_list(data: dict[str, Any], key: str, where: str) -> tuple[str, ...]:
    values = _get(data, key, list, where)
    if not all(isinstance(v, str) for v in values):
        raise ConfigError(f"{where}: '{key}' must be a list of strings")
    return tuple(values)


def parse_app(data: dict[str, Any]) -> AppConfig:
    ui = _get(data, "ui", dict, "app.yaml")
    hotkey = _get(data, "hotkey", dict, "app.yaml")
    ext = _get(data, "extraction", dict, "app.yaml")
    lang = _get(data, "language", dict, "app.yaml")
    debug = _get(data, "debug", dict, "app.yaml")
    mode = _get(ext, "mode", str, "app.yaml extraction")
    if mode not in EXTRACTION_MODES:
        raise ConfigError(f"app.yaml extraction: mode must be one of {EXTRACTION_MODES}")
    policy = _get(lang, "policy", str, "app.yaml language")
    if policy not in ("mirror", "fixed"):
        raise ConfigError("app.yaml language: policy must be 'mirror' or 'fixed'")
    return AppConfig(
        always_on_top=_get(ui, "always_on_top", bool, "app.yaml ui"),
        notify_on_draft=_get(ui, "notify_on_draft", bool, "app.yaml ui"),
        hotkey=HotkeyConfig(
            shortcut_id=_get(hotkey, "shortcut_id", str, "app.yaml hotkey"),
            description=_get(hotkey, "description", str, "app.yaml hotkey"),
            preferred_trigger=_get(hotkey, "preferred_trigger", str, "app.yaml hotkey"),
        ),
        extraction=ExtractionConfig(
            mode=mode,
            ocr_languages=_get(ext, "ocr_languages", str, "app.yaml extraction"),
            min_confidence=_get(ext, "min_confidence", float, "app.yaml extraction"),
            min_characters=_get(ext, "min_characters", int, "app.yaml extraction"),
        ),
        language=LanguageConfig(
            policy=policy,
            fixed=_get(lang, "fixed", str, "app.yaml language"),
            supported=_str_list(lang, "supported", "app.yaml language"),
        ),
        save_debug_captures=_get(debug, "save_captures", bool, "app.yaml debug"),
        log_message_text=_get(debug, "log_message_text", bool, "app.yaml debug"),
    )


def parse_backends(data: dict[str, Any]) -> BackendsConfig:
    entries = _get(data, "backends", list, "backends.yaml")
    backends = []
    for index, entry in enumerate(entries):
        where = f"backends.yaml backends[{index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{where}: must be a mapping")
        url = _get(entry, "url", str, where)
        if urlparse(url).scheme not in ("http", "https"):
            raise ConfigError(f"{where}: url must start with http:// or https://")
        models = (
            _get(entry, "model_preferences", dict, where) if "model_preferences" in entry else {}
        )
        backends.append(
            BackendConfig(
                name=_get(entry, "name", str, where),
                label=str(entry.get("label", entry["name"])),
                url=url.rstrip("/"),
                priority=_get(entry, "priority", int, where),
                connect_timeout_ms=_get(entry, "connect_timeout_ms", int, where),
                request_timeout_s=_get(entry, "request_timeout_s", float, where),
                reply_models=_str_list(models, "reply", where) if "reply" in models else (),
                vision_models=_str_list(models, "vision", where) if "vision" in models else (),
            )
        )
    names = [b.name for b in backends]
    if len(set(names)) != len(names):
        raise ConfigError("backends.yaml: backend names must be unique")
    return BackendsConfig(
        health_cache_seconds=_get(data, "health_cache_seconds", float, "backends.yaml"),
        backends=tuple(sorted(backends, key=lambda b: b.priority)),
    )


def parse_reply_rules(data: dict[str, Any]) -> ReplyRules:
    raw_categories = _get(data, "categories", dict, "reply_rules.yaml")
    unknown = set(raw_categories) - set(CATEGORIES)
    if unknown:
        raise ConfigError(f"reply_rules.yaml: unknown categories {sorted(unknown)}")
    missing = set(CATEGORIES) - set(raw_categories)
    if missing:
        raise ConfigError(f"reply_rules.yaml: missing categories {sorted(missing)}")
    categories = {}
    for name, entry in raw_categories.items():
        where = f"reply_rules.yaml categories.{name}"
        if not isinstance(entry, dict):
            raise ConfigError(f"{where}: must be a mapping")
        categories[name] = CategoryPolicy(
            policy=_get(entry, "policy", str, where),
            prompt=_get(entry, "prompt", str, where),
            max_words=_get(entry, "max_words", int, where),
        )
    rules = []
    for index, entry in enumerate(_get(data, "rules", list, "reply_rules.yaml")):
        where = f"reply_rules.yaml rules[{index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{where}: must be a mapping")
        category = _get(entry, "category", str, where)
        if category not in CATEGORIES:
            raise ConfigError(f"{where}: unknown category '{category}'")
        keywords = _str_list(entry, "keywords", where)
        min_hits = _get(entry, "min_hits", int, where)
        if not 1 <= min_hits <= len(keywords):
            raise ConfigError(f"{where}: min_hits must be between 1 and the number of keywords")
        rules.append(
            ClassificationRule(_get(entry, "id", str, where), category, keywords, min_hits)
        )
    return ReplyRules(
        style=_str_list(data, "style", "reply_rules.yaml"),
        categories=categories,
        rules=tuple(rules),
    )


def parse_user_profile(data: dict[str, Any]) -> UserProfile:
    where = "user_profile.yaml"
    return UserProfile(
        name=_get(data, "name", str, where),
        sign_off=_get(data, "sign_off", str, where),
        sign_off_de=_get(data, "sign_off_de", str, where),
        allowed_facts=_str_list(data, "allowed_facts", where),
        mention_facts_in=_str_list(data, "mention_facts_in", where),
        recruiting_preference=_get(data, "recruiting_preference", str, where),
    )


PROMPT_NAMES = ("system.md", "classifier.md")


def load_config(user_dir: Path | None = None) -> Config:
    """Load and validate all configuration files. Raises ConfigError with a readable message."""
    user_dir = user_config_dir() if user_dir is None else user_dir
    rules = parse_reply_rules(_read_yaml("reply_rules.yaml", user_dir))
    prompt_files = set(PROMPT_NAMES) | {c.prompt for c in rules.categories.values()}
    prompts = {name: _read_text(f"prompts/{name}", user_dir) for name in sorted(prompt_files)}
    return Config(
        app=parse_app(_read_yaml("app.yaml", user_dir)),
        backends=parse_backends(_read_yaml("backends.yaml", user_dir)),
        reply_rules=rules,
        user_profile=parse_user_profile(_read_yaml("user_profile.yaml", user_dir)),
        prompts=prompts,
    )
