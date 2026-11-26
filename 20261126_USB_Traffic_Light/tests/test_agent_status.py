# SPDX-License-Identifier: GPL-3.0-or-later
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from threading import Thread
from unittest.mock import Mock, patch

from websockets.sync.server import unix_serve

import agent_status as monitor
from agent_status import State


class StatusTest(unittest.TestCase):
    def test_priority(self):
        for states, color in (
            ([], "off"),
            ([State.IDLE], "off"),
            ([State.RUNNING], "green"),
            ([State.RUNNING, State.WAITING], "yellow"),
            ([State.WAITING, State.BLOCKED, State.RUNNING], "red"),
            ([State.RUNNING, State.UNKNOWN], "off"),
        ):
            self.assertEqual(monitor.color_for(states), color)

    def test_claude_states(self):
        for row, expected in (
            ({"state": "blocked", "status": "waiting"}, State.WAITING),
            ({"state": "blocked"}, State.BLOCKED),
            ({"state": "working", "status": "busy"}, State.RUNNING),
            ({"state": "failed"}, State.BLOCKED),
            ({"status": "busy"}, State.RUNNING),
            ({"status": "shell"}, State.IDLE),
            ({"status": "new"}, State.UNKNOWN),
        ):
            self.assertEqual(monitor.claude_state(row), expected)

    def test_codex_states(self):
        for status, goal, expected in (
            ({"type": "systemError"}, {}, State.BLOCKED),
            ({"type": "active"}, {"status": "blocked"}, State.BLOCKED),
            ({"type": "idle"}, {"status": "budgetLimited"}, State.BLOCKED),
            (
                {"type": "active", "activeFlags": ["waitingOnApproval"]},
                {},
                State.WAITING,
            ),
            (
                {"type": "active", "activeFlags": ["waitingOnUserInput"]},
                {},
                State.WAITING,
            ),
            ({"type": "active", "activeFlags": []}, {}, State.RUNNING),
            ({"type": "notLoaded"}, {}, State.IDLE),
            ({"type": "other"}, {}, State.UNKNOWN),
        ):
            self.assertEqual(monitor.codex_state(status, goal), expected)

    def test_quota_only_blocks_exhaustion_before_reset(self):
        for value, reset, expected in (
            (100, 20, True),
            (100, 10, False),
            (99, 20, False),
        ):
            self.assertEqual(monitor.exhausted(value, reset, now=10), expected)
        self.assertFalse(monitor.exhausted(None, 20, now=10))

    def test_codex_window_exhaustion(self):
        quota = {"rateLimits": {"secondary": {"usedPercent": 100, "resetsAt": 20}}}
        self.assertTrue(monitor.codex_quota(quota, 10))
        self.assertFalse(monitor.codex_quota(quota, 20))

    def test_profiles_skip_missing_and_report_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for name in (".claude", ".claude-dmo", ".codex"):
                (home / name).mkdir()
            codex = Mock()
            codex.status.return_value = [State.RUNNING]
            with patch.object(
                monitor, "claude_status", side_effect=([State.WAITING], OSError())
            ):
                self.assertEqual(
                    monitor.read_profiles(home, {"codex": codex}, 10),
                    {
                        "claude": [State.WAITING],
                        "claude-dmo": [State.UNKNOWN],
                        "codex": [State.RUNNING],
                    },
                )

    def test_claude_cli_and_quota_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            cache = home / "abtop-rate-limits.json"
            cache.write_text(
                json.dumps(
                    {
                        "updated_at": 10,
                        "five_hour": {"used_percentage": 100, "resets_at": 1000},
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(monitor.subprocess, "run") as run:
                run.return_value.stdout = '[{"status":"busy"}]'
                self.assertEqual(
                    monitor.claude_status(home, 20), [State.RUNNING, State.BLOCKED]
                )
                self.assertEqual(
                    run.call_args.kwargs["env"]["CLAUDE_CONFIG_DIR"], str(home)
                )
                self.assertEqual(monitor.claude_status(home, 400), [State.RUNNING])
                run.return_value.stdout = "{}"
                with self.assertRaises(ValueError):
                    monitor.claude_status(home, 20)
                run.return_value.stdout = "[]"
                self.assertEqual(monitor.claude_status(home, 20), [])
                cache.write_text("broken", encoding="utf-8")
                run.return_value.stdout = '[{"status":"busy"}]'
                self.assertEqual(monitor.claude_status(home, 20), [State.RUNNING])


class CodexSocketTest(unittest.TestCase):
    def test_waiting_thread_and_quota_poll(self):
        methods = []

        def handler(connection):
            for message in connection:
                request = json.loads(message)
                method = request["method"]
                methods.append(method)
                if method == "initialized":
                    continue
                result = {
                    "initialize": {},
                    "thread/loaded/list": {"data": ["thread"]},
                    "thread/read": {
                        "thread": {
                            "status": {
                                "type": "active",
                                "activeFlags": ["waitingOnUserInput"],
                            }
                        }
                    },
                    "thread/goal/get": {"goal": None},
                    "account/rateLimits/read": {"ordinaryUsageAllowed": False},
                }[method]
                connection.send(json.dumps({"id": request["id"], "result": result}))

        with tempfile.TemporaryDirectory() as directory:
            socket = Path(directory) / "app-server-control.sock"
            with unix_serve(handler, str(socket)) as server:
                worker = Thread(target=server.serve_forever)
                worker.start()
                self.addCleanup(worker.join)
                self.addCleanup(server.shutdown)
                source = monitor.CodexSource(socket)
                self.assertEqual(source.status(10), [State.WAITING, State.BLOCKED])
                self.assertEqual(source.status(20), [State.WAITING, State.BLOCKED])
        self.assertEqual(methods.count("account/rateLimits/read"), 1)

    def test_paginated_rpc_skips_notifications_and_handles_optional_errors(self):
        connection = Mock()
        connection.recv.side_effect = [
            '{"method":"notification"}',
            '{"id":1,"result":{}}',
            '{"id":2,"result":{"data":[],"nextCursor":"next"}}',
            '{"id":3,"result":{"data":["thread"]}}',
            '{"id":4,"result":{"thread":{"status":{"type":"idle"}}}}',
            '{"id":5,"error":{}}',
            '{"id":6,"error":{}}',
        ]
        with patch.object(monitor, "unix_connect") as connect:
            connect.return_value.__enter__.return_value = connection
            self.assertEqual(
                monitor.CodexSource(Path("socket")).status(10), [State.IDLE]
            )
        requests = [json.loads(call.args[0]) for call in connection.send.call_args_list]
        self.assertEqual(requests[3]["params"], {"cursor": "next"})

    def test_preserves_a_blocker_when_threads_vanish_or_return_invalid_json(self):
        connection = Mock()
        connection.recv.side_effect = [
            '{"id":1,"result":{}}',
            '{"id":2,"result":{"data":["blocked","closed","malformed","running"]}}',
            '{"id":3,"result":{"thread":{"status":{"type":"systemError"}}}}',
            '{"id":4,"result":{"goal":null}}',
            '{"id":5,"error":{"code":-32602}}',
            "[]",
            '{"id":7,"result":{"thread":{"status":{"type":"active","activeFlags":[]}}}}',
            '{"id":8,"result":{"goal":null}}',
            '{"id":9,"result":{"rateLimits":["invalid"]}}',
        ]
        with patch.object(monitor, "unix_connect") as connect:
            connect.return_value.__enter__.return_value = connection
            states = monitor.CodexSource(Path("socket")).status(10)
        self.assertEqual(
            states, [State.BLOCKED, State.UNKNOWN, State.UNKNOWN, State.RUNNING]
        )
        self.assertEqual(monitor.color_for(states), "red")

    def test_repeated_pagination_preserves_previous_results(self):
        connection = Mock()
        connection.recv.side_effect = [
            '{"id":1,"result":{}}',
            '{"id":2,"result":{"data":["thread"],"nextCursor":"repeat"}}',
            '{"id":3,"result":{"thread":{"status":{"type":"active","activeFlags":["waitingOnApproval"]}}}}',
            '{"id":4,"result":{"goal":null}}',
            '{"id":5,"result":{"data":[],"nextCursor":"repeat"}}',
            '{"id":6,"result":{}}',
        ]
        with patch.object(monitor, "unix_connect") as connect:
            connect.return_value.__enter__.return_value = connection
            self.assertEqual(
                monitor.CodexSource(Path("socket")).status(10),
                [State.WAITING, State.UNKNOWN],
            )

    def test_invalid_list_is_unknown(self):
        for row in ('{"noData":true}', '{"data":[1]}'):
            with (
                self.subTest(row=row),
                patch.object(monitor, "unix_connect") as connect,
            ):
                connection = connect.return_value.__enter__.return_value
                connection.recv.side_effect = [
                    '{"id":1,"result":{}}',
                    '{"id":2,"result":' + row + "}",
                    '{"id":3,"result":{}}',
                ]
                self.assertEqual(
                    monitor.CodexSource(Path("socket")).status(10), [State.UNKNOWN]
                )

    def test_invalid_status_is_detected(self):
        with self.assertRaises(ValueError):
            monitor.codex_state(None, {})

    def test_rpc_stops_at_deadline(self):
        with (
            patch.object(monitor, "unix_connect"),
            patch.object(monitor.time, "monotonic", side_effect=(0, 0, 4)),
            self.assertRaises(TimeoutError),
        ):
            monitor.CodexSource(Path("socket")).status(10)


class CliTest(unittest.TestCase):
    def test_dry_run_and_usb(self):
        with (
            patch.object(
                monitor, "read_profiles", return_value={"claude-dmo": [State.WAITING]}
            ),
            patch.object(monitor, "show_color") as show,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            monitor.main(["--once", "--dry-run"])
            show.assert_not_called()
            self.assertIn("yellow", output.getvalue())
            monitor.main(["--once", "--usb-port", "1-2"])
            show.assert_called_once_with("yellow", "1-2")

    def test_reports_usb_failure_and_recovers_on_later_scan(self):
        with (
            patch.object(
                monitor, "read_profiles", return_value={"claude": [State.RUNNING]}
            ),
            patch.object(
                monitor,
                "show_color",
                side_effect=[OSError("unplugged"), OSError("unplugged"), None, None],
            ) as show,
            patch.object(
                monitor.time, "sleep", side_effect=[None, None, KeyboardInterrupt]
            ),
            contextlib.redirect_stdout(io.StringIO()) as output,
            contextlib.redirect_stderr(io.StringIO()) as errors,
        ):
            monitor.main([])
            self.assertEqual(
                [call.args[0] for call in show.call_args_list],
                ["green", "green", "green", "off"],
            )
            status_lines = output.getvalue().splitlines()[1:]
            self.assertEqual(len(status_lines), 2)
            self.assertIn(
                "usb=unavailable shown=red:0,yellow:0,green:0,off:0", status_lines[0]
            )
            self.assertTrue(
                status_lines[1].endswith("shown=red:0,yellow:0,green:1,off:0")
            )
            self.assertEqual(errors.getvalue(), "unplugged\n")
            show.side_effect = OSError("unplugged")
            with self.assertRaises(SystemExit) as failure:
                monitor.main(["--once"])
            self.assertEqual(failure.exception.code, 1)

    def test_termination_signal_requests_cleanup(self):
        with self.assertRaises(KeyboardInterrupt):
            monitor.on_terminate(monitor.signal.SIGTERM, None)

    def test_interrupted_dry_run_leaves_the_light_alone(self):
        with (
            patch.object(monitor, "read_profiles", side_effect=KeyboardInterrupt),
            patch.object(monitor, "show_color") as show,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            monitor.main(["--dry-run"])
        show.assert_not_called()

    def test_monitor_can_stop_after_the_light_is_unplugged(self):
        with (
            patch.object(
                monitor, "read_profiles", return_value={"claude": [State.RUNNING]}
            ),
            patch.object(
                monitor, "show_color", side_effect=[None, OSError("unplugged")]
            ),
            patch.object(monitor.time, "sleep", side_effect=KeyboardInterrupt),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()) as errors,
        ):
            monitor.main([])
            self.assertEqual(errors.getvalue(), "unplugged\n")

    def test_real_output_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "hid"
            with patch.object(monitor, "find_device", return_value=fixture):
                monitor.show_color("yellow")
                self.assertEqual(
                    fixture.read_bytes(), bytes.fromhex("00001000 00001200 00001101")
                )
                monitor.show_color("off")
                self.assertEqual(
                    fixture.read_bytes(), bytes.fromhex("00001000 00001100 00001200")
                )

    def test_counts_distinct_display_periods_and_reports_version(self):
        observations = [
            {"claude": [State.RUNNING]},
            {"claude": [State.RUNNING, State.IDLE]},
            {"claude": [State.WAITING]},
            {"claude": [State.BLOCKED]},
            {"claude": [State.RUNNING]},
            {"claude": [State.IDLE]},
        ]
        with (
            patch.object(monitor, "read_profiles", side_effect=observations),
            patch.object(monitor, "show_color"),
            patch.object(
                monitor.time, "sleep", side_effect=[None] * 5 + [KeyboardInterrupt]
            ),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            monitor.main([])
        banner, first, same, waiting, blocked, running, idle = (
            output.getvalue().splitlines()
        )
        self.assertRegex(banner, r"^Cleware agent monitor [0-9]+\.[0-9]+\.[0-9]+$")
        self.assertIn("shown=red:0,yellow:0,green:1,off:0", first)
        self.assertIn("shown=red:0,yellow:0,green:1,off:0", same)
        self.assertTrue(waiting.endswith("shown=red:0,yellow:1,green:1,off:0"))
        self.assertTrue(blocked.endswith("shown=red:1,yellow:1,green:1,off:0"))
        self.assertTrue(running.endswith("shown=red:1,yellow:1,green:2,off:0"))
        self.assertTrue(idle.endswith("shown=red:1,yellow:1,green:2,off:1"))

    def test_dry_run_counts_without_usb_and_version_exits_before_scanning(self):
        with (
            patch.object(
                monitor, "read_profiles", return_value={"claude": [State.WAITING]}
            ) as read,
            patch.object(monitor, "show_color") as show,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            with self.assertRaises(SystemExit) as exit_status:
                monitor.main(["--version"])
            self.assertEqual(exit_status.exception.code, 0)
            read.assert_not_called()
            monitor.main(["--dry-run", "--once"])
            show.assert_not_called()
        self.assertIn("planned=red:0,yellow:1,green:0,off:0", output.getvalue())

    def test_normal_cli_entrypoint(self):
        result = subprocess.run(
            [monitor.sys.executable, "agent_status.py", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        self.assertIn("--dry-run", result.stdout)
