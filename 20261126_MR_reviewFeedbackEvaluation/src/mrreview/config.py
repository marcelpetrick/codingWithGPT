# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Configuration from an optional TOML file plus environment variables (REQ-LLM-1).

Secrets come only from the environment. A token in the file is refused.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from datetime import date
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_OLLAMA_URL = "http://192.168.100.67:11434"
DEFAULT_MODEL = "qwen3.6:35b-a3b-q4_K_M-agentic"


class ConfigError(ValueError):
    """The configuration is not valid."""


@dataclass(frozen=True)
class Config:
    """All settings. Defaults match VISION.md."""

    gitlab_url: str = ""
    gitlab_token: str = field(default="", repr=False)
    discover_membership_only: bool = False
    include_archived: bool = False
    db_path: Path = Path("data/mrreview.sqlite3")
    window_months: int = 12
    min_window_mrs: int = 1
    per_page: int = 100
    http_timeout_s: float = 30.0
    max_retries: int = 5
    backoff_base_s: float = 1.0
    max_diff_bytes: int = 200_000
    ollama_url: str = DEFAULT_OLLAMA_URL
    ollama_model: str = DEFAULT_MODEL
    ollama_timeout_s: float = 600.0
    ollama_concurrency: int = 1
    ollama_keep_alive: str = "15m"
    ollama_options: dict[str, Any] = field(
        default_factory=lambda: {"temperature": 0, "num_ctx": 16384}
    )
    max_note_graphemes: int = 1500
    max_thread_notes: int = 30
    timezone: str = "Europe/Berlin"
    business_start_hour: int = 8
    business_end_hour: int = 18
    holidays: tuple[date, ...] = ()
    censor_days: int = 14

    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


_ENV = {
    "MRREVIEW_GITLAB_URL": "gitlab_url",
    "MRREVIEW_GITLAB_TOKEN": "gitlab_token",
    "MRREVIEW_DB": "db_path",
    "MRREVIEW_OLLAMA_URL": "ollama_url",
    "MRREVIEW_OLLAMA_MODEL": "ollama_model",
}


def _check(cfg: Config) -> Config:
    for name in ("window_months", "per_page", "max_retries", "censor_days", "min_window_mrs"):
        value = getattr(cfg, name)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            or (value == 0 and name in {"window_months", "per_page"})
        ):
            raise ConfigError(f"{name} must be a positive integer")
    if not isinstance(cfg.ollama_concurrency, int) or cfg.ollama_concurrency < 1:
        raise ConfigError("ollama_concurrency must be at least 1")
    if not 0 <= cfg.business_start_hour < cfg.business_end_hour <= 24:
        raise ConfigError("business hours must satisfy 0 <= start < end <= 24")
    try:
        ZoneInfo(cfg.timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ConfigError(f"unknown timezone {cfg.timezone!r}") from exc
    return cfg


def load_config(path: Path | None, env: Mapping[str, str]) -> Config:
    """Build the configuration: defaults, then the TOML file, then the environment."""
    values: dict[str, Any] = {}
    known = {f.name for f in fields(Config)}
    if path is not None:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if "gitlab_token" in data:
            raise ConfigError("put gitlab_token in the environment (MRREVIEW_GITLAB_TOKEN)")
        unknown = set(data) - known
        if unknown:
            raise ConfigError(f"unknown configuration keys: {sorted(unknown)}")
        values.update(data)
    for var, name in _ENV.items():
        if env.get(var):
            values[name] = env[var]
    if "db_path" in values:
        values["db_path"] = Path(values["db_path"])
    if "gitlab_url" in values:
        values["gitlab_url"] = str(values["gitlab_url"]).rstrip("/")
    if "holidays" in values:
        try:
            values["holidays"] = tuple(
                d if isinstance(d, date) else date.fromisoformat(str(d)) for d in values["holidays"]
            )
        except ValueError as exc:
            raise ConfigError("holidays must be ISO dates") from exc
    return _check(Config(**values))
