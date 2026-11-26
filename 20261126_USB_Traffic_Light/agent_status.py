# SPDX-License-Identifier: GPL-3.0-or-later
"""Show the status of local Claude and Codex agents on a Cleware light."""

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from enum import StrEnum
from pathlib import Path

from websockets.exceptions import WebSocketException
from websockets.sync.client import unix_connect

from traffic_light import find_device, set_lights

POLL_SECONDS = 5
QUOTA_SECONDS = 60
CLAUDE_QUOTA_MAX_AGE = 300
READ_ERRORS = (OSError, ValueError, subprocess.SubprocessError, WebSocketException)


class State(StrEnum):
    BLOCKED = "blocked"
    WAITING = "waiting"
    RUNNING = "running"
    IDLE = "idle"
    UNKNOWN = "unavailable"


def color_for(states):
    states = set(states)
    for state, color in (
        (State.BLOCKED, "red"),
        (State.WAITING, "yellow"),
        (State.UNKNOWN, "off"),
        (State.RUNNING, "green"),
    ):
        if state in states:
            return color
    return "off"


def claude_state(row):
    state, status = row.get("state"), row.get("status")
    if state == "failed":
        return State.BLOCKED
    if status == "waiting":
        return State.WAITING
    if state == "blocked":
        return State.BLOCKED
    if state == "working" or status == "busy":
        return State.RUNNING
    if state in {"done", "stopped"} or status in {"idle", "shell"}:
        return State.IDLE
    return State.UNKNOWN


def codex_state(status, goal):
    kind = status.get("type")
    if kind == "systemError" or goal.get("status") in {
        "blocked",
        "budgetLimited",
        "usageLimited",
    }:
        return State.BLOCKED
    if kind == "active":
        if set(status.get("activeFlags", [])) & {
            "waitingOnApproval",
            "waitingOnUserInput",
        }:
            return State.WAITING
        return State.RUNNING
    return State.IDLE if kind in {"idle", "notLoaded"} else State.UNKNOWN


def exhausted(used, resets_at, now):
    return (
        type(used) in {int, float}
        and used >= 100
        and type(resets_at) in {int, float}
        and resets_at > now
    )


def claude_quota(root, now):
    try:
        cache = json.loads(
            (root / "abtop-rate-limits.json").read_text(encoding="utf-8")
        )
        age = now - cache["updated_at"]
        return 0 <= age <= CLAUDE_QUOTA_MAX_AGE and any(
            exhausted(window.get("used_percentage"), window.get("resets_at"), now)
            for name in ("five_hour", "seven_day")
            if isinstance(window := cache.get(name), dict)
        )
    except OSError, ValueError, KeyError, TypeError:
        return False


def claude_status(root, now):
    result = subprocess.run(
        ["claude", "agents", "--json"],
        env={**os.environ, "CLAUDE_CONFIG_DIR": str(root)},
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        encoding="utf-8",
        timeout=4,
        check=True,
    )
    rows = json.loads(result.stdout)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Invalid Claude status")
    states = [claude_state(row) for row in rows]
    if states and claude_quota(root, now):
        states.append(State.BLOCKED)
    return states


class CodexSource:
    def __init__(self, path):
        self.path = path
        self.next_quota = 0
        self.quota = {}

    def status(self, now):
        with unix_connect(
            str(self.path), uri="ws://localhost/", open_timeout=2, close_timeout=0.2
        ) as connection:
            request_id = 0

            def rpc(method, **params):
                nonlocal request_id
                request_id += 1
                connection.send(
                    json.dumps({"method": method, "id": request_id, "params": params})
                )
                deadline = time.monotonic() + 3
                while (remaining := deadline - time.monotonic()) > 0:
                    response = json.loads(connection.recv(timeout=remaining))
                    if response.get("id") != request_id:
                        continue
                    if not isinstance(result := response.get("result"), dict):
                        raise ValueError(f"Codex request failed: {method}")
                    return result
                raise TimeoutError("Codex response timed out")

            rpc(
                "initialize",
                clientInfo={"name": "cleware_status_light", "version": "0.1.0"},
            )
            connection.send('{"method":"initialized"}')
            states = []
            params = {}
            while True:
                page = rpc("thread/loaded/list", **params)
                for thread_id in page["data"]:
                    thread = rpc("thread/read", threadId=thread_id, includeTurns=False)[
                        "thread"
                    ]
                    try:
                        goal = rpc("thread/goal/get", threadId=thread_id).get("goal")
                    except ValueError:
                        goal = None
                    states.append(codex_state(thread["status"], goal or {}))
                cursor = page.get("nextCursor")
                if not cursor:
                    break
                params = {"cursor": cursor}

            if states and now >= self.next_quota:
                self.next_quota = now + QUOTA_SECONDS
                try:
                    self.quota = rpc("account/rateLimits/read")
                except READ_ERRORS:
                    self.quota = {}
            if states and codex_quota(self.quota, now):
                states.append(State.BLOCKED)
            return states


def codex_quota(quota, now):
    if quota.get("ordinaryUsageAllowed") is False:
        return True
    limits = quota.get("rateLimits") or {}
    return any(
        exhausted(window.get("usedPercent"), window.get("resetsAt"), now)
        for name in ("primary", "secondary")
        if isinstance(window := limits.get(name), dict)
    )


def read_profiles(home, codex, now):
    result = {}
    for name in ("claude", "claude-dmo", "codex", "codex-dmo"):
        root = home / f".{name}"
        if not root.is_dir():
            continue
        try:
            result[name] = (
                codex[name].status(now) if name in codex else claude_status(root, now)
            )
        except (*READ_ERRORS, KeyError, TypeError):
            result[name] = [State.UNKNOWN]
    return result


def show_color(color):
    with find_device(None).open("wb", buffering=0) as device:
        fcntl.flock(device, fcntl.LOCK_EX)
        set_lights(device, () if color == "off" else (color,))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Check once and exit")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print status without writing to USB"
    )
    args = parser.parse_args(argv)

    home = Path.home()
    codex = {
        name: CodexSource(home / f".{name}/app-server-control/app-server-control.sock")
        for name in ("codex", "codex-dmo")
    }
    previous = None
    last_usb_error = None
    try:
        while True:
            profiles = read_profiles(home, codex, time.time())
            color = color_for(state for states in profiles.values() for state in states)
            parts = [
                f"{name}={','.join(sorted(states)) or 'idle'}"
                for name, states in profiles.items()
            ]
            line = " ".join([color, *parts])
            if line != previous:
                print(line, flush=True)
                previous = line
            if not args.dry_run:
                try:
                    show_color(color)
                    last_usb_error = None
                except OSError as error:
                    if args.once:
                        parser.exit(1, f"{error}\n")
                    if str(error) != last_usb_error:
                        print(error, file=sys.stderr, flush=True)
                        last_usb_error = str(error)
            if args.once:
                return
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
