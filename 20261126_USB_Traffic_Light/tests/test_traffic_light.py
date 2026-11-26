# SPDX-License-Identifier: GPL-3.0-or-later
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import traffic_light as light


class ReportsTest(unittest.TestCase):
    def test_short_write_fails(self):
        device = Mock()
        with (
            patch.object(light.os, "write", return_value=3),
            self.assertRaisesRegex(OSError, "Incomplete USB report for red"),
        ):
            light.write_channel(device, "red", 1)


class CommandsTest(unittest.TestCase):
    def setUp(self):
        workspace = self.enterContext(tempfile.TemporaryDirectory())
        self.directory = Path(workspace)
        self.enterContext(patch.object(light, "DEVICE_DIR", self.directory))
        self.wait = self.enterContext(patch.object(light.time, "sleep"))
        self.stdout = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.device = self.add_device("63813")

    def add_device(self, serial):
        device = self.directory / f"usb-Cleware_GmbH_USB-Ampel_{serial}-hidraw"
        device.touch()
        return device

    def run_cli(self, *args):
        with patch.object(sys, "argv", ["traffic_light.py", *args]):
            return light.main()

    def check_cli_error(self, expected, *args, code=1):
        with (
            contextlib.redirect_stderr(io.StringIO()) as stderr,
            self.assertRaises(SystemExit) as error,
        ):
            self.run_cli(*args)
        self.assertEqual(error.exception.code, code)
        self.assertIn(expected, stderr.getvalue())

    def test_two_colors_and_all_three(self):
        self.assertEqual(self.run_cli("set", "red", "yellow"), 0)
        self.assertEqual(
            self.device.read_bytes(), bytes.fromhex("00001200 00001001 00001101")
        )
        self.assertEqual(self.run_cli("set", "red", "yellow", "green"), 0)
        self.assertEqual(
            self.device.read_bytes(), bytes.fromhex("00001001 00001101 00001201")
        )

    def test_off(self):
        self.assertEqual(self.run_cli("off"), 0)
        self.assertEqual(
            self.device.read_bytes(), bytes.fromhex("00001000 00001100 00001200")
        )

    def test_flash(self):
        for interval, state in [("0.5", "10"), ("1", "11"), ("2", "12")]:
            with self.subTest(interval=interval):
                self.assertEqual(self.run_cli("flash", interval, "green"), 0)
                self.assertEqual(
                    self.device.read_bytes(),
                    bytes.fromhex(f"00001000 00001100 000012{state}"),
                )

    def test_cycle(self):
        self.assertEqual(self.run_cli("cycle"), 0)
        self.assertEqual(self.stdout.getvalue(), "red\nyellow\ngreen\n")
        self.assertEqual(
            [call.args for call in self.wait.call_args_list], [(1,), (1,), (1,)]
        )
        self.assertEqual(
            self.device.read_bytes(),
            bytes.fromhex(
                "00001100 00001200 00001001 "
                "00001000 00001200 00001101 "
                "00001000 00001100 00001201 "
                "00001000 00001100 00001200"
            ),
        )

    def test_interrupted_cycle_switches_all_colors_off(self):
        self.wait.side_effect = KeyboardInterrupt
        self.assertEqual(self.run_cli("cycle"), 130)
        self.assertEqual(
            self.device.read_bytes(),
            bytes.fromhex("00001100 00001200 00001001 00001000 00001100 00001200"),
        )

    def test_selects_exact_usb_serial(self):
        other = self.add_device("café-信号-🚦")
        self.assertEqual(self.run_cli("--usb-serial", "café-信号-🚦", "off"), 0)
        self.assertEqual(
            other.read_bytes(), bytes.fromhex("00001000 00001100 00001200")
        )
        self.assertEqual(self.device.read_bytes(), b"")

    def test_missing_duplicate_and_invalid_arguments(self):
        self.check_cli_error("No matching", "--usb-serial", "missing", "off")
        self.add_device("another")
        self.check_cli_error("Multiple Cleware", "off")
        self.check_cli_error("invalid choice", "set", "blue", code=2)

    def test_device_permission_error(self):
        with patch.object(
            Path, "open", side_effect=PermissionError("permission denied")
        ):
            self.check_cli_error("permission denied", "off")
