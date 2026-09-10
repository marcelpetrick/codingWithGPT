# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Pure record parsers: one JSONL line (or database row) in, one event out.

Every parser cheaply rejects lines by substring before paying for
``json.loads``, because rollout files are dominated by large content records.
"""

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime, time, tzinfo
from pathlib import Path
from typing import Protocol

from tokenusage2.model import Account, Event, QuotaWindow, Tool, Usage

CODEX_WINDOWS = {300: "5h", 10080: "week"}
BACKFILL_PREFIX = "claude-daily:"


class Parser(Protocol):
    ctx: dict
    errors: int
    quotas: list[QuotaWindow]

    def feed(self, line: bytes) -> Event | None: ...


def count(value: object) -> int:
    """A non-negative integer token count, tolerating junk."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0
    return max(0, int(value))


def parse_ts(value: object) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.timestamp()


def claude_route(request_id: str) -> str:
    """Anthropic's API stamps every response with a ``req_…`` request id; local
    Anthropic-compatible servers (Ollama, proxies) do not."""
    return "anthropic" if request_id.startswith("req_") else ""


def _loads(line: bytes | str) -> dict | None:
    try:
        data = json.loads(line)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


class ClaudeParser:
    """Claude Code transcript lines (``projects/**/*.jsonl``)."""

    def __init__(self, account: str) -> None:
        self.account = account
        self.ctx: dict = {}
        self.errors = 0
        self.quotas: list[QuotaWindow] = []

    def feed(self, line: bytes) -> Event | None:
        if b'"usage"' not in line:
            return None
        obj = _loads(line)
        if obj is None:
            self.errors += 1
            return None
        message = obj.get("message")
        if obj.get("type") != "assistant" or not isinstance(message, dict):
            return None
        usage = message.get("usage")
        model = str(message.get("model") or "unknown")
        ident = message.get("id") or obj.get("uuid")
        ts = parse_ts(obj.get("timestamp"))
        if not isinstance(usage, dict) or model == "<synthetic>" or not ident or ts is None:
            return None
        details = usage.get("output_tokens_details")
        tokens = Usage(
            input=count(usage.get("input_tokens")),
            cache_read=count(usage.get("cache_read_input_tokens")),
            cache_write=count(usage.get("cache_creation_input_tokens")),
            output=count(usage.get("output_tokens")),
            reasoning=count(details.get("thinking_tokens")) if isinstance(details, dict) else 0,
        )
        if tokens.total == 0:
            return None
        request_id = str(obj.get("requestId") or "")
        return Event(
            # No account in the key: a copied home must not count a message twice.
            key=f"claude:{ident}:{request_id}",
            ts=ts,
            tool=Tool.CLAUDE,
            account=self.account,
            model=model,
            route=claude_route(request_id),
            project=str(obj.get("cwd") or ""),
            session=str(obj.get("sessionId") or ""),
            usage=tokens,
        )


def codex_usage(data: Mapping[str, object]) -> Usage:
    """Codex reports ``input_tokens`` including the cached part; split it."""
    total_input = count(data.get("input_tokens"))
    cached = min(count(data.get("cached_input_tokens")), total_input)
    written = min(count(data.get("cache_write_input_tokens")), total_input - cached)
    return Usage(
        input=total_input - cached - written,
        cache_read=cached,
        cache_write=written,
        output=count(data.get("output_tokens")),
        reasoning=count(data.get("reasoning_output_tokens")),
    )


def thread_from_filename(path: Path) -> str:
    stem = path.stem
    return stem[-36:] if len(stem) >= 36 else stem


class CodexParser:
    """Codex rollout lines (``sessions/**/rollout-*.jsonl``).

    ``token_count`` events repeat the same cumulative total whenever only the
    rate limits refresh, so the pair (thread, cumulative total) identifies one
    usage increment. ``ctx`` carries thread, model, cwd and provider across
    incremental reads of the same file.
    """

    def __init__(self, account: str, ctx: Mapping[str, object], fallback_thread: str) -> None:
        self.account = account
        self.ctx: dict = dict(ctx)
        self.ctx.setdefault("thread", fallback_thread)
        self.errors = 0
        self.quotas: list[QuotaWindow] = []

    def feed(self, line: bytes) -> Event | None:
        if b'"token_count"' in line:
            return self._token_count(line)
        if b'"session_meta"' in line or b'"turn_context"' in line:
            self._context(line)
        return None

    def _context(self, line: bytes) -> None:
        obj = _loads(line)
        if obj is None:
            self.errors += 1
            return
        payload = obj.get("payload")
        if not isinstance(payload, dict):
            return
        if obj.get("type") == "session_meta" and not self.ctx.get("meta"):
            self.ctx["meta"] = True
            if payload.get("id"):
                self.ctx["thread"] = str(payload["id"])
            self.ctx["cwd"] = str(payload.get("cwd") or "")
            self.ctx["provider"] = str(payload.get("model_provider") or "openai")
        elif obj.get("type") == "turn_context" and payload.get("model"):
            self.ctx["model"] = str(payload["model"])

    def _rate_limits(self, limits: object, ts: float) -> None:
        if not isinstance(limits, dict) or limits.get("limit_id") not in {None, "codex"}:
            return
        for slot in ("primary", "secondary"):
            window = limits.get(slot)
            if not isinstance(window, dict):
                continue
            used = window.get("used_percent")
            if isinstance(used, bool) or not isinstance(used, int | float):
                continue
            minutes = count(window.get("window_minutes"))
            resets = window.get("resets_at")
            self.quotas.append(
                QuotaWindow(
                    account=self.account,
                    window=CODEX_WINDOWS.get(minutes, f"{minutes}m"),
                    used_percent=float(used),
                    resets_at=float(resets) if isinstance(resets, int | float) else None,
                    observed_at=ts,
                    source="codex rollout",
                    plan=str(limits["plan_type"]) if limits.get("plan_type") else None,
                )
            )

    def _token_count(self, line: bytes) -> Event | None:
        obj = _loads(line)
        if obj is None:
            self.errors += 1
            return None
        payload = obj.get("payload")
        ts = parse_ts(obj.get("timestamp"))
        if obj.get("type") != "event_msg" or not isinstance(payload, dict) or ts is None:
            return None
        if payload.get("type") != "token_count":
            return None
        self._rate_limits(payload.get("rate_limits"), ts)
        info = payload.get("info")
        if not isinstance(info, dict):
            return None
        total = info.get("total_token_usage")
        last = info.get("last_token_usage")
        if not isinstance(total, dict) or not isinstance(last, dict):
            return None
        cumulative = count(total.get("total_tokens"))
        tokens = codex_usage(last)
        if cumulative == 0 or tokens.total == 0:
            return None
        thread = str(self.ctx["thread"])
        return Event(
            key=f"codex:{self.account}:{thread}:{cumulative}",
            ts=ts,
            tool=Tool.CODEX,
            account=self.account,
            model=str(self.ctx.get("model") or "unknown"),
            route=str(self.ctx.get("provider") or "openai"),
            project=str(self.ctx.get("cwd") or ""),
            session=thread,
            usage=tokens,
        )


def make_parser(account: Account, ctx: Mapping[str, object], path: Path) -> Parser:
    if account.tool is Tool.CODEX:
        return CodexParser(account.id, ctx, thread_from_filename(path))
    return ClaudeParser(account.id)


def parse_opencode_message(account: str, row_id: str, data: str | bytes) -> Event | None:
    """One row of OpenCode's ``message`` table."""
    obj = _loads(data)
    if obj is None or obj.get("role") != "assistant":
        return None
    tokens = obj.get("tokens")
    times = obj.get("time")
    if not isinstance(tokens, dict) or not isinstance(times, dict):
        return None
    created = times.get("created")
    if isinstance(created, bool) or not isinstance(created, int | float):
        return None
    cache = tokens.get("cache") if isinstance(tokens.get("cache"), dict) else {}
    fresh = count(tokens.get("input"))
    output = count(tokens.get("output"))
    reasoning = count(tokens.get("reasoning"))
    read, write = count(cache.get("read")), count(cache.get("write"))
    # OpenCode keeps reasoning apart from output unless its own total says otherwise.
    if tokens.get("total") != fresh + output + read + write:
        output += reasoning
    usage = Usage(
        input=fresh, cache_read=read, cache_write=write, output=output, reasoning=reasoning
    )
    if usage.total == 0:
        return None
    path = obj.get("path") if isinstance(obj.get("path"), dict) else {}
    return Event(
        key=f"opencode:{account}:{row_id}",
        ts=created / 1000.0,
        tool=Tool.OPENCODE,
        account=account,
        model=str(obj.get("modelID") or "unknown"),
        route=str(obj.get("providerID") or "unknown"),
        project=str(path.get("cwd") or ""),
        session=str(obj.get("sessionID") or ""),
        usage=usage,
    )


def parse_stats_cache(
    account: str,
    data: Mapping[str, object],
    before: date | None,
    tz: tzinfo,
) -> list[Event]:
    """Claude's retained daily totals, only for days before the first transcript.

    The split into input/cache/output is not retained, so the tokens are
    recorded as ``unsplit`` and drawn hatched.
    """
    events = []
    days = data.get("dailyModelTokens")
    for day in days if isinstance(days, list) else []:
        if not isinstance(day, dict) or not isinstance(day.get("tokensByModel"), dict):
            continue
        try:
            when = date.fromisoformat(str(day.get("date")))
        except ValueError:
            continue
        if before is not None and when >= before:
            continue
        noon = datetime.combine(when, time(12), tzinfo=tz).timestamp()
        for model, tokens in day["tokensByModel"].items():
            if count(tokens) == 0:
                continue
            model = str(model)
            events.append(
                Event(
                    key=f"{BACKFILL_PREFIX}{account}:{when.isoformat()}:{model}",
                    ts=noon,
                    tool=Tool.CLAUDE,
                    account=account,
                    model=model,
                    route="anthropic" if model.startswith("claude-") else "",
                    project="(retained daily total)",
                    session="",
                    usage=Usage(unsplit=count(tokens)),
                )
            )
    return events


def parse_claude_quota(
    account: str, data: Mapping[str, object], fallback_ts: float, source: str
) -> list[QuotaWindow]:
    """A Claude Code statusline snapshot with ``five_hour``/``seven_day`` windows."""
    observed = data.get("updated_at")
    observed_at = float(observed) if isinstance(observed, int | float) else fallback_ts
    quotas = []
    for key, name in (("five_hour", "5h"), ("seven_day", "week")):
        window = data.get(key)
        if not isinstance(window, dict):
            continue
        used = window.get("used_percentage", window.get("used_percent"))
        if isinstance(used, bool) or not isinstance(used, int | float):
            continue
        resets = window.get("resets_at")
        quotas.append(
            QuotaWindow(
                account=account,
                window=name,
                used_percent=float(used),
                resets_at=float(resets) if isinstance(resets, int | float) and resets else None,
                observed_at=observed_at,
                source=source,
            )
        )
    return quotas
