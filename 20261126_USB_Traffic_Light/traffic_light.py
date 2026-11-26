#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Control a Cleware USB-Ampel (0d50:0008) through Linux hidraw."""

import argparse
import fcntl
import os
import time
from pathlib import Path

CHANNELS = {"red": 0x10, "yellow": 0x11, "green": 0x12}
FLASH = {"0.5": 16, "1": 17, "2": 18}
DEVICE_DIR = Path("/dev")
HIDRAW_SYSFS_DIR = Path("/sys/class/hidraw")
HID_ID = "0003:00000D50:00000008"


def find_device(serial, port=None):
    devices = []
    for entry in sorted(HIDRAW_SYSFS_DIR.glob("hidraw*")):
        try:
            hid = (entry / "device").resolve(strict=True)
            uevent = (hid / "uevent").read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        properties = dict(
            line.split("=", 1) for line in uevent.splitlines() if "=" in line
        )
        if properties.get("HID_ID") != HID_ID:
            continue
        if serial is not None and properties.get("HID_UNIQ") != serial:
            continue
        if port is not None and port not in hid.parts:
            continue
        devices.append(DEVICE_DIR / entry.name)
    if not devices:
        raise OSError("No matching Cleware USB-Ampel found")
    if len(devices) > 1:
        raise OSError(
            "Multiple Cleware USB-Ampel devices found. Use --usb-serial or --usb-port."
        )
    return devices[0]


def write_channel(device, color, state):
    # hidraw expects a leading zero for an unnumbered report.
    report = bytes((0, 0, CHANNELS[color], state))
    if os.write(device.fileno(), report) != len(report):
        raise OSError(f"Incomplete USB report for {color}")


def set_lights(device, colors, state=1):
    """Set the selected colors and switch all other colors off."""
    for color in CHANNELS:
        if color not in colors:
            write_channel(device, color, 0)
    for color in CHANNELS:
        if color in colors:
            write_channel(device, color, state)


def cycle(device):
    try:
        for color in CHANNELS:
            set_lights(device, (color,))
            print(color, flush=True)
            time.sleep(1)
    finally:
        set_lights(device, ())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usb-serial", help="USB descriptor serial string")
    parser.add_argument("--usb-port", help="Linux USB port path, for example 3-2.1.4")
    commands = parser.add_subparsers(dest="command", required=True)
    steady = commands.add_parser("set", help="Turn on the listed colors")
    steady.add_argument("colors", nargs="+", choices=CHANNELS)
    commands.add_parser("off", help="Turn all colors off")
    commands.add_parser("cycle", help="Show red, yellow and green for one second each")
    blink = commands.add_parser("flash", help="Use the device's built-in flashing")
    blink.add_argument("interval", choices=FLASH, help="Flash interval in seconds")
    blink.add_argument("colors", nargs="+", choices=CHANNELS)

    args = parser.parse_args()
    try:
        path = find_device(args.usb_serial, args.usb_port)
        with path.open("wb", buffering=0) as device:
            fcntl.flock(device, fcntl.LOCK_EX)
            if args.command == "cycle":
                cycle(device)
            elif args.command == "set":
                set_lights(device, args.colors)
            elif args.command == "flash":
                set_lights(device, args.colors, FLASH[args.interval])
            else:
                set_lights(device, ())
    except KeyboardInterrupt:
        return 130
    except OSError as error:
        parser.exit(1, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
