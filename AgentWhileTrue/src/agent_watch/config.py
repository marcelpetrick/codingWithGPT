"""Layered configuration: defaults < config file < environment < CLI.

The v0 file format from the vision is a plain ``KEY=VALUE`` file, which is
readable by both this tool and by shell. It is parsed as data, never executed -
sourcing a config file would hand arbitrary code execution to anything that can
write it, which is not a trade worth making for a tool whose whole job is to
type into terminals.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, fields, replace
from enum import StrEnum
from pathlib import Path

APP_NAME = "agent-watch"

_DURATION_RE = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>ms|s|m|h)?$", re.IGNORECASE)
_UNIT_SECONDS = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}
_ENV_PREFIX = "AGENT_WATCH_"


class ConfigError(ValueError):
    """The configuration could not be understood.

    Raised rather than silently defaulted: a misspelled ``RESET_GRACE`` that
    quietly becomes 60 seconds is exactly the kind of surprise this tool cannot
    afford.
    """


class Mode(StrEnum):
    """How much the supervisor is allowed to do."""

    OBSERVE = "observe"
    ASK = "ask"
    AUTO = "auto"

    @property
    def may_send_input(self) -> bool:
        return self is not Mode.OBSERVE


def parse_duration(text: str, *, field_name: str = "duration") -> float:
    """Parse ``60``, ``60s``, ``90s``, ``2m`` or ``1h`` into seconds."""
    match = _DURATION_RE.match(text.strip())
    if match is None:
        raise ConfigError(f"{field_name}: cannot parse duration {text!r}")
    return float(match.group("value")) * _UNIT_SECONDS[(match.group("unit") or "s").lower()]


def parse_bool(text: str, *, field_name: str = "flag") -> bool:
    lowered = text.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ConfigError(f"{field_name}: cannot parse boolean {text!r}")


def xdg_dir(env_var: str, default_relative: str) -> Path:
    value = os.environ.get(env_var)
    base = Path(value) if value else Path.home() / default_relative
    return base / APP_NAME


def default_state_dir() -> Path:
    return xdg_dir("XDG_STATE_HOME", ".local/state")


def default_config_path() -> Path:
    return xdg_dir("XDG_CONFIG_HOME", ".config") / "config"


def default_runtime_dir() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    # Falling back to the state directory keeps the lock working on systems
    # without a runtime dir; it is still under the user's own home.
    return Path(runtime) / APP_NAME if runtime else default_state_dir()


@dataclass(frozen=True, slots=True)
class Policy:
    """What classes of action are permitted, independently of the mode.

    Everything that costs money or silently degrades the model stays off.
    """

    resume_after_reset: bool = True
    auto_accept_model_downgrade: bool = False
    auto_use_paid_credits: bool = False
    auto_buy_credits: bool = False
    auto_consume_reset_credit: bool = False
    #: Claude's resume is a bare Enter on an explicit "press enter to continue"
    #: affordance. Codex has no such affordance: resuming means typing text into
    #: the composer, which is strictly more dangerous, so it stays opt-in.
    allow_codex_auto_resume: bool = False


@dataclass(frozen=True, slots=True)
class Config:
    """The effective configuration for one run."""

    mode: Mode = Mode.ASK
    scan_interval: float = 2.0
    usage_poll_interval: float = 60.0
    reset_grace: float = 60.0
    max_resume_attempts: int = 3
    retry_delays: tuple[float, ...] = (5.0, 30.0, 60.0)
    visible_lines: int = 40
    log_file: Path | None = None
    state_dir: Path | None = None
    runtime_dir: Path | None = None
    allow_root: bool = False
    use_fzf: bool = True
    policy: Policy = Policy()

    def resolved_state_dir(self) -> Path:
        return self.state_dir or default_state_dir()

    def resolved_runtime_dir(self) -> Path:
        return self.runtime_dir or default_runtime_dir()

    def resolved_log_file(self) -> Path:
        return self.log_file or (self.resolved_state_dir() / f"{APP_NAME}.log")

    def retry_delay(self, attempt: int) -> float:
        """Delay before ``attempt`` (1-based), clamped to the last entry."""
        if attempt <= 0:
            return 0.0
        index = min(attempt, len(self.retry_delays)) - 1
        return self.retry_delays[index]


#: Config-file / environment key -> (target attribute, parser). The policy keys
#: are addressed with a ``policy.`` prefix in the mapping and unpacked below.
_KEYS: dict[str, tuple[str, str]] = {
    "MODE": ("mode", "mode"),
    "SCAN_INTERVAL": ("scan_interval", "duration"),
    "USAGE_POLL_INTERVAL": ("usage_poll_interval", "duration"),
    "RESET_GRACE": ("reset_grace", "duration"),
    "MAX_RESUME_ATTEMPTS": ("max_resume_attempts", "int"),
    "RETRY_DELAYS": ("retry_delays", "durations"),
    "VISIBLE_LINES": ("visible_lines", "int"),
    "LOG_FILE": ("log_file", "path"),
    "STATE_DIR": ("state_dir", "path"),
    "RUNTIME_DIR": ("runtime_dir", "path"),
    "ALLOW_ROOT": ("allow_root", "bool"),
    "USE_FZF": ("use_fzf", "bool"),
    "RESUME_AFTER_RESET": ("policy.resume_after_reset", "bool"),
    "AUTO_ACCEPT_MODEL_DOWNGRADE": ("policy.auto_accept_model_downgrade", "bool"),
    "AUTO_USE_PAID_CREDITS": ("policy.auto_use_paid_credits", "bool"),
    "AUTO_BUY_CREDITS": ("policy.auto_buy_credits", "bool"),
    "AUTO_CONSUME_RESET_CREDIT": ("policy.auto_consume_reset_credit", "bool"),
    "ALLOW_CODEX_AUTO_RESUME": ("policy.allow_codex_auto_resume", "bool"),
}


def _coerce(kind: str, raw: str, key: str):
    if kind == "duration":
        return parse_duration(raw, field_name=key)
    if kind == "durations":
        return tuple(parse_duration(part, field_name=key) for part in raw.replace(",", " ").split())
    if kind == "bool":
        return parse_bool(raw, field_name=key)
    if kind == "int":
        try:
            return int(raw.strip())
        except ValueError as exc:
            raise ConfigError(f"{key}: cannot parse integer {raw!r}") from exc
    if kind == "path":
        return Path(os.path.expandvars(raw.strip())).expanduser()
    if kind == "mode":
        try:
            return Mode(raw.strip().lower())
        except ValueError as exc:
            raise ConfigError(f"{key}: unknown mode {raw!r}") from exc
    raise ConfigError(f"{key}: unsupported value kind {kind!r}")  # pragma: no cover


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_config_text(text: str) -> dict[str, str]:
    """Parse ``KEY=VALUE`` lines. Comments and blank lines are ignored."""
    values: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ConfigError(f"config line {number}: expected KEY=VALUE, got {line!r}")
        key, _, value = stripped.partition("=")
        values[key.strip().upper()] = _strip_quotes(value)
    return values


def _apply(config: Config, values: dict[str, str], source: str) -> Config:
    updates: dict[str, object] = {}
    policy_updates: dict[str, object] = {}
    for key, raw in values.items():
        target = _KEYS.get(key)
        if target is None:
            raise ConfigError(f"{source}: unknown setting {key!r}")
        attribute, kind = target
        coerced = _coerce(kind, raw, key)
        if attribute.startswith("policy."):
            policy_updates[attribute.removeprefix("policy.")] = coerced
        else:
            updates[attribute] = coerced
    if policy_updates:
        updates["policy"] = replace(config.policy, **policy_updates)  # type: ignore[arg-type]
    return replace(config, **updates)  # type: ignore[arg-type]


def from_environ(environ: dict[str, str] | None = None) -> dict[str, str]:
    """Collect ``AGENT_WATCH_*`` variables, plus the bare names from the vision.

    The vision's example config uses bare names such as ``RESET_GRACE``; those
    are honoured too, but only for keys this tool actually owns, so an unrelated
    ``MODE`` in the environment cannot reconfigure the supervisor.
    """
    env = os.environ if environ is None else environ
    collected: dict[str, str] = {}
    for key, value in env.items():
        if key.startswith(_ENV_PREFIX):
            bare = key.removeprefix(_ENV_PREFIX)
            if bare in _KEYS:
                collected[bare] = value
    return collected


def load(
    *,
    config_path: Path | None = None,
    environ: dict[str, str] | None = None,
    overrides: dict[str, str] | None = None,
) -> Config:
    """Build the effective configuration.

    Precedence, lowest to highest: dataclass defaults, the config file, the
    ``AGENT_WATCH_*`` environment, then explicit CLI overrides.
    """
    config = Config()
    path = config_path or default_config_path()
    if path.is_file():
        config = _apply(config, parse_config_text(path.read_text(encoding="utf-8")), str(path))
    config = _apply(config, from_environ(environ), "environment")
    if overrides:
        config = _apply(config, {k.upper(): v for k, v in overrides.items()}, "command line")
    return config


def describe(config: Config) -> list[tuple[str, str]]:
    """Flatten the configuration for ``agent-watch config``."""
    rows: list[tuple[str, str]] = []
    for spec in fields(Config):
        if spec.name == "policy":
            continue
        rows.append((spec.name, str(getattr(config, spec.name))))
    for spec in fields(Policy):
        rows.append((f"policy.{spec.name}", str(getattr(config.policy, spec.name))))
    rows.append(("resolved_log_file", str(config.resolved_log_file())))
    rows.append(("resolved_state_dir", str(config.resolved_state_dir())))
    rows.append(("resolved_runtime_dir", str(config.resolved_runtime_dir())))
    return rows
