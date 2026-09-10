# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Find every local Claude Code, Codex and OpenCode home — nothing is hardcoded.

Candidates come from, in priority order: the config file, the environment
(``CLAUDE_CONFIG_DIR``, ``CODEX_HOME``), the environment of running agent
processes (read from ``/proc``), assignments in shell rc files (for
launchers such as ``codex-work() { CODEX_HOME=~/.codex-work codex; }``), the
tools' default locations, and a scan of ``$HOME`` for ``.claude*``/``.codex*``
directories. A candidate only becomes an account when its content proves it:
a ``projects/`` tree for Claude Code, ``sessions/`` or ``auth.json`` for Codex.

Shell rc files are also mined for ``ANTHROPIC_BASE_URL`` launchers, which tells
which Ollama host or proxy served a locally routed model.
"""

import base64
import binascii
import json
import os
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
from urllib.parse import urlsplit

from tokenusage2.config import Config, expand
from tokenusage2.model import Account, Tool
from tokenusage2.procscan import HOME_VARIABLE, AgentProcess

RC_FILES = (
    ".zshrc",
    ".zshenv",
    ".zprofile",
    ".bashrc",
    ".bash_profile",
    ".profile",
    ".config/fish/config.fish",
)
_HOME_VARIABLES = {"CLAUDE_CONFIG_DIR": Tool.CLAUDE, "CODEX_HOME": Tool.CODEX}
_ASSIGN = re.compile(
    r"""(?:^|[\s;({])(?:export\s+|local\s+|declare\s+-x\s+)?"""
    r"""([A-Za-z_][A-Za-z0-9_]*)=("([^"]*)"|'([^']*)'|([^\s;'"()]+))"""
)
_FISH_SET = re.compile(r"^\s*set\s+(?:-[A-Za-z]+\s+)*([A-Za-z_][A-Za-z0-9_]*)\s+(\S+)")
_FUNCTION = re.compile(
    r"^\s*(?:function\s+([A-Za-z_][\w.:-]*)\s*(?:\(\))?|([A-Za-z_][\w.:-]*)\s*\(\))\s*\{?"
)
_ALIAS = re.compile(r"""^\s*alias\s+([A-Za-z_][\w.:-]*)=(['"])(.*)\2\s*$""")
_MODEL_FLAG = re.compile(r"""--model[= ]\s*("[^"]+"|'[^']+'|[^\s;]+)""")
_REFERENCE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")


@dataclass(frozen=True, slots=True)
class BackendHint:
    """A shell launcher that points Claude Code at a non-Anthropic endpoint."""

    launcher: str
    base_url: str
    models: tuple[str, ...]
    source: str

    @property
    def label(self) -> str:
        return backend_label(self.base_url)


@dataclass(frozen=True, slots=True)
class BackendMap:
    """Model name → backend label; user globs override launcher hints."""

    hints: Mapping[str, str] = field(default_factory=dict)
    globs: tuple[tuple[str, str], ...] = ()

    def override(self, model: str) -> str | None:
        for pattern, label in self.globs:
            if fnmatchcase(model, pattern):
                return label
        return None

    def hint(self, model: str) -> str | None:
        return self.hints.get(model)


@dataclass(frozen=True, slots=True)
class Discovery:
    accounts: tuple[Account, ...]
    hints: tuple[BackendHint, ...]
    backends: BackendMap
    rc_files: tuple[Path, ...]
    notes: tuple[str, ...]


def backend_label(url: str) -> str:
    """Short, credential-free name for an endpoint: ``ollama@host`` or ``host:port``."""
    parts = urlsplit(url if "://" in url else f"http://{url}")
    host = parts.hostname or url
    try:
        port = parts.port
    except ValueError:
        port = None
    if port == 11434:
        return f"ollama@{host}"
    return f"{host}:{port}" if port else host


def _sanitize_url(url: str) -> str:
    parts = urlsplit(url if "://" in url else f"http://{url}")
    netloc = parts.hostname or ""
    try:
        if parts.port:
            netloc = f"{netloc}:{parts.port}"
    except ValueError:
        pass
    return f"{parts.scheme}://{netloc}{parts.path}".rstrip("/")


def display_path(path: Path, home: Path) -> str:
    try:
        return "~/" + str(path.relative_to(home))
    except ValueError:
        return str(path)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return {}
    return data if isinstance(data, dict) else {}


# --- shell rc mining ---------------------------------------------------------


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def rc_home_assignments(texts: Mapping[Path, str]) -> list[tuple[Tool, str, str]]:
    """Every ``CLAUDE_CONFIG_DIR``/``CODEX_HOME`` value assigned in the rc files."""
    found = []
    for path, text in texts.items():
        for line in text.splitlines():
            if line.lstrip().startswith("#"):
                continue
            pairs = [
                (m.group(1), next(g for g in m.group(3, 4, 5) if g is not None))
                for m in _ASSIGN.finditer(line)
            ]
            fish = _FISH_SET.match(line)
            if fish:
                pairs.append((fish.group(1), _unquote(fish.group(2))))
            for name, value in pairs:
                if name in _HOME_VARIABLES and value:
                    found.append((_HOME_VARIABLES[name], value, path.name))
    return found


def _block_hint(name: str, lines: Iterable[str], source: str) -> BackendHint | None:
    variables: dict[str, str] = {}
    flagged: list[str] = []
    for line in lines:
        for match in _ASSIGN.finditer(line):
            variables[match.group(1)] = next(g for g in match.group(3, 4, 5) if g is not None)
        flagged.extend(_unquote(value) for value in _MODEL_FLAG.findall(line))
    base = variables.get("ANTHROPIC_BASE_URL")
    if not base:
        return None

    def resolve(value: str) -> str:
        return _REFERENCE.sub(lambda m: variables.get(m.group(1), m.group(0)), value)

    base = resolve(base)
    if "$" in base:
        return None
    candidates = [
        value
        for key, value in variables.items()
        if key.startswith("ANTHROPIC_") and key.endswith("MODEL")
    ]
    models: list[str] = []
    for value in (*flagged, *candidates):
        model = resolve(value)
        if model and "$" not in model and model not in models:
            models.append(model)
    return BackendHint(name, _sanitize_url(base), tuple(models), source)


def backend_hints(texts: Mapping[Path, str]) -> list[BackendHint]:
    """Launchers (functions and aliases) that set ``ANTHROPIC_BASE_URL``."""
    hints: list[BackendHint] = []

    def add(hint: BackendHint | None) -> None:
        if hint is not None:
            hints.append(hint)

    for path, text in texts.items():
        current: str | None = None
        body: list[str] = []
        shell: list[str] = []
        for line in text.splitlines():
            if line.lstrip().startswith("#"):
                continue
            if current is None:
                alias = _ALIAS.match(line)
                if alias:
                    add(_block_hint(alias.group(1), [alias.group(3)], path.name))
                    continue
                function = _FUNCTION.match(line)
                if function:
                    current = function.group(1) or function.group(2)
                    rest = line[function.end() :]
                    if rest.rstrip().endswith("}"):
                        add(_block_hint(current, [rest], path.name))
                        current = None
                    else:
                        body = [rest]
                    continue
                shell.append(line)
            elif line.startswith("}"):
                add(_block_hint(current, body, path.name))
                current = None
            else:
                body.append(line)
        add(_block_hint("(shell)", shell, path.name))
    return hints


# --- identities --------------------------------------------------------------


def decode_jwt_claims(token: object) -> dict:
    """Claims of a JWT payload, without verification. Never returns the token."""
    if not isinstance(token, str) or token.count(".") < 2:
        return {}
    payload = token.split(".")[1]
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except ValueError, binascii.Error:
        return {}
    return data if isinstance(data, dict) else {}


def _pretty_tier(value: str) -> str:
    for prefix in ("default_claude_", "claude_", "default_"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    return value.replace("_", " ")


def claude_identity(claude_home: Path, home: Path) -> tuple[str | None, str | None]:
    candidates = [claude_home / ".claude.json"]
    if claude_home == home / ".claude":
        candidates.insert(0, home / ".claude.json")
    for candidate in candidates:
        data = _load_json(candidate)
        if not data:
            continue
        account = data.get("oauthAccount")
        if isinstance(account, dict) and account.get("emailAddress"):
            # A personal tier ("default_claude_max_20x") is the most specific;
            # the organization type ("claude_pro") names the plan otherwise.
            tier = (
                account.get("userRateLimitTier")
                or account.get("organizationType")
                or account.get("billingType")
            )
            return str(account["emailAddress"]), _pretty_tier(str(tier)) if tier else None
        if data.get("primaryApiKey"):
            return "API key", None
    return None, None


def codex_identity(codex_home: Path) -> tuple[str | None, str | None]:
    auth = _load_json(codex_home / "auth.json")
    if not auth:
        return None, None
    tokens = auth.get("tokens")
    claims = decode_jwt_claims(tokens.get("id_token")) if isinstance(tokens, dict) else {}
    email = claims.get("email")
    openai = claims.get("https://api.openai.com/auth")
    plan = openai.get("chatgpt_plan_type") if isinstance(openai, dict) else None
    if email:
        return str(email), str(plan) if plan else None
    if auth.get("OPENAI_API_KEY") or str(auth.get("auth_mode", "")).startswith("api"):
        return "API key", None
    return None, None


# --- homes -------------------------------------------------------------------


def _is_claude_home(path: Path) -> bool:
    return (path / "projects").is_dir()


def _is_codex_home(path: Path) -> bool:
    return (path / "sessions").is_dir() or (path / "auth.json").is_file()


def _scan(directory: Path, prefix: str) -> list[Path]:
    try:
        entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
    except OSError:
        return []
    return [Path(e.path) for e in entries if e.name.startswith(prefix) and e.is_dir()]


def _label(path: Path, home: Path, config: Config, xdg_config: Path) -> str:
    configured = config.labels.get(str(path)) or config.labels.get(display_path(path, home))
    if configured:
        return configured
    name = path.name.lstrip(".") or path.name
    return f"{name}-xdg" if path.parent == xdg_config else name


def process_hints(processes: Sequence[AgentProcess]) -> list[BackendHint]:
    """Running Claude Code processes started against a non-Anthropic endpoint."""
    hints = []
    for process in processes:
        base = process.env.get("ANTHROPIC_BASE_URL")
        if process.tool is Tool.CLAUDE and base and process.model:
            hints.append(
                BackendHint(
                    f"pid {process.pid}", _sanitize_url(base), (process.model,), "running process"
                )
            )
    return hints


def discover(
    home: Path, env: Mapping[str, str], config: Config, processes: Sequence[AgentProcess] = ()
) -> Discovery:
    """Discover accounts and backend hints for ``home``."""
    xdg_config = Path(env.get("XDG_CONFIG_HOME") or home / ".config")
    xdg_data = Path(env.get("XDG_DATA_HOME") or home / ".local" / "share")
    rc_paths = (
        config.rc_files if config.rc_files is not None else tuple(home / name for name in RC_FILES)
    )
    rc_texts = {path: _read(path) for path in rc_paths if path.is_file()}
    rc_homes = rc_home_assignments(rc_texts)
    hints = process_hints(processes) + backend_hints(rc_texts)
    notes: list[str] = []

    candidates: dict[Tool, list[tuple[Path, str]]] = {tool: [] for tool in Tool}
    candidates[Tool.CLAUDE] += [(path, "config") for path in config.claude_homes]
    candidates[Tool.CODEX] += [(path, "config") for path in config.codex_homes]
    candidates[Tool.OPENCODE] += [(path, "config") for path in config.opencode_dbs]
    for variable, tool in _HOME_VARIABLES.items():
        if env.get(variable):
            candidates[tool].append((expand(env[variable], home, env), "env"))
    for process in processes:
        variable = HOME_VARIABLE.get(process.tool)
        if variable and process.env.get(variable):
            path = expand(process.env[variable], home, env)
            candidates[process.tool].append((path, f"process {process.pid}"))
    for tool, raw, source in rc_homes:
        candidates[tool].append((expand(raw, home, env), f"rc:{source}"))
    candidates[Tool.CLAUDE] += [(home / ".claude", "default"), (xdg_config / "claude", "default")]
    candidates[Tool.CODEX].append((home / ".codex", "default"))
    candidates[Tool.OPENCODE].append((xdg_data / "opencode" / "opencode.db", "default"))
    if config.scan_home:
        candidates[Tool.CLAUDE] += [(p, "scan") for p in _scan(home, ".claude")]
        candidates[Tool.CLAUDE] += [(p, "scan") for p in _scan(xdg_config, "claude")]
        candidates[Tool.CODEX] += [(p, "scan") for p in _scan(home, ".codex")]
        candidates[Tool.CODEX] += [(p, "scan") for p in _scan(xdg_config, "codex")]

    valid = {
        Tool.CLAUDE: _is_claude_home,
        Tool.CODEX: _is_codex_home,
        Tool.OPENCODE: Path.is_file,
    }
    ignored = {path.resolve() for path in config.ignore}
    accounts: list[Account] = []
    seen: set[Path] = set()
    labels: set[str] = set()
    for tool in Tool:
        for path, origin in candidates[tool]:
            resolved = path.resolve()
            if resolved in seen:
                continue
            if resolved in ignored:
                notes.append(f"ignored by config: {display_path(path, home)}")
                seen.add(resolved)
                continue
            if not valid[tool](path):
                if origin not in {"default", "scan"}:
                    notes.append(f"{tool} home without data ({origin}): {display_path(path, home)}")
                continue
            seen.add(resolved)
            if tool is Tool.CLAUDE:
                identity, plan = claude_identity(path, home)
            elif tool is Tool.CODEX:
                identity, plan = codex_identity(path)
            else:
                identity, plan = None, None
            label = "opencode" if tool is Tool.OPENCODE else _label(path, home, config, xdg_config)
            base, suffix = label, 2
            while label in labels:
                label, suffix = f"{base}-{suffix}", suffix + 1
            labels.add(label)
            accounts.append(
                Account(
                    id=f"{tool}:{display_path(path, home)}",
                    tool=tool,
                    home=path,
                    label=label,
                    identity=identity,
                    plan=plan,
                    origin=origin,
                )
            )

    model_hints: dict[str, str] = {}
    for hint in hints:
        for model in hint.models:
            model_hints.setdefault(model, hint.label)
    return Discovery(
        accounts=tuple(accounts),
        hints=tuple(hints),
        backends=BackendMap(model_hints, tuple(config.backends.items())),
        rc_files=tuple(rc_texts),
        notes=tuple(notes),
    )
