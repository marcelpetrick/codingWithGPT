"""Integration tests for the small deployment shell scripts."""

from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).parents[1]
PROXY = ROOT / "scripts" / "claude-statusline-proxy.sh"


def _run_proxy(
    state_home: Path, used: int = 100, *, chain: str = ""
) -> subprocess.CompletedProcess:
    payload = json.dumps(
        {
            "usage": {
                "five_hour": {
                    "utilization": used,
                    "resets_at": "2026-09-06T01:20:00Z",
                },
                "seven_day": {"utilization": 42},
            }
        }
    )
    environment = {**os.environ, "XDG_STATE_HOME": str(state_home)}
    if chain:
        environment["AGENT_WATCH_STATUSLINE_CHAIN"] = chain
    return subprocess.run(
        [str(PROXY)], input=payload, text=True, capture_output=True, env=environment, timeout=5
    )


def test_statusline_proxy_captures_quota_and_chains_payload(tmp_path: Path) -> None:
    chained = tmp_path / "chained.json"
    result = _run_proxy(tmp_path, chain=f"tee {chained}")
    assert result.returncode == 0
    captured = json.loads((tmp_path / "agent-watch/quota/claude.json").read_text())
    assert captured["source"] == "claude"
    assert captured["five_hour"]["utilization"] == 100
    assert json.loads(chained.read_text())["usage"]["seven_day"]["utilization"] == 42


def test_statusline_proxy_concurrent_writes_remain_valid(tmp_path: Path) -> None:
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda used: _run_proxy(tmp_path, used), range(90, 106)))
    assert all(result.returncode == 0 for result in results)
    captured = json.loads((tmp_path / "agent-watch/quota/claude.json").read_text())
    assert captured["five_hour"]["utilization"] in range(90, 106)
    assert not list((tmp_path / "agent-watch/quota").glob("*.tmp.*"))


def test_statusline_proxy_fails_open_on_bad_input(tmp_path: Path) -> None:
    result = subprocess.run(
        [str(PROXY)],
        input="not-json",
        text=True,
        capture_output=True,
        env={**os.environ, "XDG_STATE_HOME": str(tmp_path)},
        timeout=5,
    )
    assert result.returncode == 0
    assert not (tmp_path / "agent-watch/quota/claude.json").exists()
