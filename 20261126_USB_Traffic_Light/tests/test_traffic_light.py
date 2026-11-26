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
        self.sysfs = self.directory / "sysfs"
        self.sysfs.mkdir()
        self.enterContext(patch.object(light, "HIDRAW_SYSFS_DIR", self.sysfs))
        self.wait = self.enterContext(patch.object(light.time, "sleep"))
        self.stdout = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.device = self.add_device("63813")

    def add_device(self, serial, port=None):
        index = len(list(self.sysfs.iterdir()))
        node = f"hidraw{index}"
        port = port or f"1-{index+1}"
        entry = self.sysfs / node
        entry.mkdir()
        hid = self.directory / "devices" / port / f"{port}:1.0" / node
        hid.mkdir(parents=True)
        (entry / "device").symlink_to(hid, target_is_directory=True)
        (hid / "uevent").write_text(
            f"HID_ID=0003:00000D50:00000008\nHID_UNIQ={serial}\n", encoding="utf-8"
        )
        device = self.directory / node
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

    def test_identical_descriptor_serials_require_a_usb_port(self):
        other = self.add_device("63813", port="1-2")
        self.check_cli_error("Multiple Cleware", "--usb-serial", "63813", "off")
        self.assertEqual(self.run_cli("--usb-port", "1-2", "set", "red"), 0)
        self.assertEqual(
            other.read_bytes(), bytes.fromhex("00001100 00001200 00001001")
        )
        self.assertEqual(self.device.read_bytes(), b"")

    def test_ignores_disappeared_and_unrelated_hid_nodes(self):
        (self.sysfs / "hidraw9").mkdir()
        unrelated = self.add_device("other")
        event = self.sysfs / unrelated.name / "device" / "uevent"
        event.write_text("HID_ID=0003:00000000:00000000\n", encoding="utf-8")
        self.assertEqual(light.find_device(None), self.device)

    def test_device_permission_error(self):
        with patch.object(
            Path, "open", side_effect=PermissionError("permission denied")
        ):
            self.check_cli_error("permission denied", "off")
