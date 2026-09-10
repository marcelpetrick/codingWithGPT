# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Optional user configuration, read from ``$XDG_CONFIG_HOME/tokenusage2/config.toml``.

Everything here is optional: discovery works without a file. The file only
adds homes that cannot be found automatically, hides homes, renames accounts
and pins models to backend labels.
"""

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

_VARIABLE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")


class ConfigError(ValueError):
    """The configuration file exists but cannot be used."""


@dataclass(frozen=True, slots=True)
class Config:
    claude_homes: tuple[Path, ...] = ()
    codex_homes: tuple[Path, ...] = ()
    opencode_dbs: tuple[Path, ...] = ()
    ignore: tuple[Path, ...] = ()
    scan_home: bool = True
    rc_files: tuple[Path, ...] | None = None
    labels: Mapping[str, str] = field(default_factory=dict)
    backends: Mapping[str, str] = field(default_factory=dict)
    source: Path | None = None


def expand(raw: str, home: Path, env: Mapping[str, str]) -> Path:
    """Expand ``~`` and ``$VARS`` against the given home and environment."""
    value = raw.strip()
    if value == "~" or value.startswith("~/"):
        value = str(home) + value[1:]
    scope = {**env, "HOME": str(home)}
    value = _VARIABLE.sub(lambda match: scope.get(match.group(1), match.group(0)), value)
    return Path(value)


def default_config_path(home: Path, env: Mapping[str, str]) -> Path:
    base = env.get("XDG_CONFIG_HOME") or str(home / ".config")
    return Path(base) / "tokenusage2" / "config.toml"


def _paths(table: Mapping[str, object], key: str, home: Path, env: Mapping[str, str]) -> tuple:
    raw = table.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigError(f"discovery.{key} must be a list of paths")
    return tuple(expand(item, home, env) for item in raw)


def _strings(data: Mapping[str, object], key: str) -> dict[str, str]:
    raw = data.get(key, {})
    if not isinstance(raw, dict) or not all(isinstance(v, str) for v in raw.values()):
        raise ConfigError(f"[{key}] must map strings to strings")
    return dict(raw)


def load_config(path: Path | None, home: Path, env: Mapping[str, str]) -> Config:
    """Load ``path`` (or the default location). A missing file is an empty config."""
    target = path or default_config_path(home, env)
    if not target.is_file():
        if path is not None:
            raise ConfigError(f"config file not found: {path}")
        return Config()
    try:
        data = tomllib.loads(target.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"{target}: {error}") from error
    discovery = data.get("discovery", {})
    if not isinstance(discovery, dict):
        raise ConfigError("[discovery] must be a table")
    scan_home = discovery.get("scan_home", True)
    if not isinstance(scan_home, bool):
        raise ConfigError("discovery.scan_home must be true or false")
    rc_files = _paths(discovery, "rc_files", home, env) if "rc_files" in discovery else None
    labels = {str(expand(k, home, env)): v for k, v in _strings(data, "labels").items()}
    return Config(
        claude_homes=_paths(discovery, "claude_homes", home, env),
        codex_homes=_paths(discovery, "codex_homes", home, env),
        opencode_dbs=_paths(discovery, "opencode_dbs", home, env),
        ignore=_paths(discovery, "ignore", home, env),
        scan_home=scan_home,
        rc_files=rc_files,
        labels=labels,
        backends=_strings(data, "backends"),
        source=target,
    )
