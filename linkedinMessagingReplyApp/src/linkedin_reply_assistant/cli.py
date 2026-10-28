# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Command line entry point `lra`."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from linkedin_reply_assistant.backends.factory import build_manager
from linkedin_reply_assistant.config.loader import ConfigError, load_config
from linkedin_reply_assistant.diagnostics.preflight import format_report, run_preflight
from linkedin_reply_assistant.version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lra",
        description="LinkedIn Reply Assistant: capture, draft, insert. Never sends.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config-dir", type=Path, help="override ~/.config/linkedin-reply-assistant"
    )
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("preflight", help="report what this desktop and the AI backends support")
    return parser


def cmd_preflight(config_dir: Path | None) -> int:
    config = load_config(config_dir)
    checks = run_preflight(build_manager(config.backends))
    print(format_report(checks))
    return 1 if any(c.status == "fail" for c in checks) else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            return cmd_preflight(args.config_dir)
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    parser.print_help()
    return 0
