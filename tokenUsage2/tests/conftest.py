# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""A fake home directory with every supported tool, built from real record shapes."""

import base64
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

BERLIN = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC).timestamp()
CODEX_THREAD = "0199aaaa-bbbb-7ccc-8ddd-eeeeeeeeeeee"
WORK_THREAD = "0199ffff-bbbb-7ccc-8ddd-000000000001"


def jwt(claims: dict) -> str:
    def encode(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{encode({'alg': 'none'})}.{encode(claims)}.signature"


def line(record: dict) -> str:
    return json.dumps(record) + "\n"


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(line(record) for record in records), encoding="utf-8")


def claude_line(
    msg_id: str,
    ts: str,
    *,
    model: str = "claude-opus-5",
    request: str | None = "req_1",
    inp: int = 10,
    cache_read: int = 1000,
    cache_write: int = 100,
    out: int = 50,
    cwd: str = "/work/alpha",
) -> dict:
    record = {
        "type": "assistant",
        "timestamp": ts,
        "sessionId": "s1",
        "cwd": cwd,
        "message": {
            "id": msg_id,
            "model": model,
            "usage": {
                "input_tokens": inp,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_write,
                "output_tokens": out,
                "output_tokens_details": {"thinking_tokens": 0},
            },
        },
    }
    if request is not None:
        record["requestId"] = request
    return record


def codex_meta(thread: str, cwd: str = "/work/beta") -> dict:
    return {
        "timestamp": "2026-09-10T08:00:00Z",
        "type": "session_meta",
        "payload": {"id": thread, "cwd": cwd, "model_provider": "openai"},
    }


def codex_turn(model: str) -> dict:
    return {
        "timestamp": "2026-09-10T08:00:01Z",
        "type": "turn_context",
        "payload": {"model": model},
    }


def codex_tokens(
    ts: str,
    cumulative: int | None,
    *,
    inp: int = 0,
    cached: int = 0,
    out: int = 0,
    reasoning: int = 0,
    primary: float | None = None,
    limit_id: str = "codex",
) -> dict:
    info = None
    if cumulative is not None:
        info = {
            "total_token_usage": {"total_tokens": cumulative},
            "last_token_usage": {
                "input_tokens": inp,
                "cached_input_tokens": cached,
                "cache_write_input_tokens": 0,
                "output_tokens": out,
                "reasoning_output_tokens": reasoning,
                "total_tokens": inp + out,
            },
        }
    limits = None
    if primary is not None:
        limits = {
            "limit_id": limit_id,
            "plan_type": "plus",
            "primary": {"used_percent": primary, "window_minutes": 300, "resets_at": NOW + 3600},
            "secondary": {"used_percent": 60.0, "window_minutes": 10080, "resets_at": NOW + 86400},
        }
    return {
        "timestamp": ts,
        "type": "event_msg",
        "payload": {"type": "token_count", "info": info, "rate_limits": limits},
    }


ZSHRC = """\
# private and company Codex logins
codex-work() { CODEX_HOME=~/.codex-work codex "$@"; }
codex-client() { CODEX_HOME=$HOME/profiles/codex-client codex "$@"; }
# CODEX_HOME=/commented/out
claude-gpu() {
  local H=http://user:secret@10.0.0.5:11434
  local M=north-mini:q4
  ANTHROPIC_AUTH_TOKEN=ollama \\
  ANTHROPIC_BASE_URL="$H" \\
  ANTHROPIC_DEFAULT_OPUS_MODEL="$M" \\
    claude --model "$M" "$@"
}
alias claude-proxy='ANTHROPIC_BASE_URL=http://localhost:4747 claude --model qwen/coder'
"""


@dataclass
class FakeHome:
    root: Path
    env: dict[str, str]

    @property
    def codex_rollout(self) -> Path:
        return (
            self.root
            / ".codex"
            / "sessions"
            / "2026"
            / "09"
            / "10"
            / f"rollout-2026-09-10T10-00-00-{CODEX_THREAD}.jsonl"
        )

    @property
    def opencode_db(self) -> Path:
        return self.root / ".local" / "share" / "opencode" / "opencode.db"


def build_home(root: Path) -> FakeHome:
    claude = root / ".claude"
    write_jsonl(
        claude / "projects" / "-work-alpha" / "s1.jsonl",
        [
            claude_line("msg_a", "2026-09-10T08:00:00Z", out=0),
            claude_line("msg_a", "2026-09-10T08:00:01Z", out=50),
            claude_line(
                "msg_b",
                "2026-09-10T09:00:00Z",
                model="north-mini:q4",
                request=None,
                inp=500,
                cache_read=0,
                cache_write=0,
                out=200,
            ),
            claude_line("msg_c", "2026-09-10T09:30:00Z", model="<synthetic>"),
            {"type": "user", "message": {"content": "what is my usage"}},
        ],
    )
    with (claude / "projects" / "-work-alpha" / "s1.jsonl").open("a") as handle:
        handle.write('{"usage": broken\n')
    (root / ".claude.json").write_text(
        json.dumps(
            {"oauthAccount": {"emailAddress": "me@example.com", "organizationType": "claude_max"}}
        )
    )
    (claude / "stats-cache.json").write_text(
        json.dumps(
            {
                "dailyModelTokens": [
                    {"date": "2026-09-01", "tokensByModel": {"claude-opus-4-7": 5000}},
                    {"date": "2026-09-10", "tokensByModel": {"claude-opus-5": 9999}},
                ],
                "modelUsage": {
                    "claude-opus-5": {
                        "inputTokens": 100,
                        "outputTokens": 100,
                        "cacheReadInputTokens": 1000,
                        "cacheCreationInputTokens": 100,
                    }
                },
            }
        )
    )
    (claude / "abtop-rate-limits.json").write_text(
        json.dumps(
            {
                "source": "claude",
                "updated_at": NOW - 60,
                "five_hour": {"used_percentage": 38, "resets_at": NOW + 3600},
                "seven_day": {"used_percentage": 49, "resets_at": NOW + 86400},
            }
        )
    )

    codex = root / ".codex"
    codex.mkdir()
    (codex / "auth.json").write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "tokens": {
                    "access_token": "SECRET-ACCESS",
                    "id_token": jwt(
                        {
                            "email": "me@example.com",
                            "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
                        }
                    ),
                },
            }
        )
    )
    home = FakeHome(root, {"HOME": str(root)})
    write_jsonl(
        home.codex_rollout,
        [
            codex_meta(CODEX_THREAD),
            codex_turn("gpt-5.6-sol"),
            codex_tokens("2026-09-10T10:00:00Z", None, primary=20.0),
            codex_tokens("2026-09-10T10:00:05Z", 1100, inp=1000, cached=600, out=100),
            codex_tokens("2026-09-10T10:00:06Z", 1100, inp=1000, cached=600, out=100, primary=22.0),
            codex_tokens("2026-09-10T10:05:00Z", 3300, inp=2000, cached=1500, out=200),
        ],
    )
    with closing(sqlite3.connect(codex / "state_5.sqlite")) as connection, connection:
        connection.execute("CREATE TABLE threads (id TEXT, tokens_used INTEGER)")
        connection.execute("INSERT INTO threads VALUES (?, 3300)", (CODEX_THREAD,))

    work = root / ".codex-work"
    work.mkdir()
    (work / "auth.json").write_text(
        json.dumps(
            {
                "tokens": {
                    "id_token": jwt(
                        {
                            "email": "work@corp.example",
                            "https://api.openai.com/auth": {"chatgpt_plan_type": "team"},
                        }
                    )
                }
            }
        )
    )
    write_jsonl(
        work
        / "sessions"
        / "2026"
        / "09"
        / "09"
        / f"rollout-2026-09-09T10-00-00-{WORK_THREAD}.jsonl",
        [
            codex_meta(WORK_THREAD, "/work/gamma"),
            codex_turn("gpt-6-astra"),
            codex_tokens("2026-09-09T10:00:00Z", 5000, inp=4000, cached=3000, out=1000),
        ],
    )
    client = root / "profiles" / "codex-client"
    client.mkdir(parents=True)
    (client / "auth.json").write_text(
        json.dumps({"auth_mode": "apikey", "OPENAI_API_KEY": "sk-secret"})
    )
    (root / ".zshrc").write_text(ZSHRC)

    home.opencode_db.parent.mkdir(parents=True)
    with closing(sqlite3.connect(home.opencode_db)) as connection, connection:
        connection.execute(
            "CREATE TABLE message (id TEXT, session_id TEXT, time_created "
            "INTEGER, time_updated INTEGER, data TEXT)"
        )
        created = int((NOW - 3600) * 1000)
        connection.execute(
            "INSERT INTO message VALUES (?, ?, ?, ?, ?)",
            (
                "msg_oc1",
                "ses1",
                created,
                created,
                json.dumps(
                    {
                        "role": "assistant",
                        "modelID": "qwen2.5-coder:7b",
                        "providerID": "ollama-local",
                        "path": {"cwd": "/work/delta"},
                        "time": {"created": created},
                        "tokens": {
                            "input": 100,
                            "output": 20,
                            "reasoning": 5,
                            "cache": {"read": 0, "write": 0},
                        },
                    }
                ),
            ),
        )
        connection.execute(
            "INSERT INTO message VALUES (?, ?, ?, ?, ?)",
            ("msg_oc0", "ses1", created - 1, created - 1, json.dumps({"role": "user"})),
        )
    return home


@pytest.fixture
def home(tmp_path: Path) -> FakeHome:
    return build_home(tmp_path / "home")
