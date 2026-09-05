"""Command-line interface.

Subcommands mirror the vision: ``run``, ``status``, ``doctor``, ``init``,
``logs``, ``config``, plus ``simulate`` for the scenario harness. Running with
no subcommand starts ``run``, because that is what the tool is for.

Two behaviours here are safety-relevant rather than cosmetic. Running under
``sudo`` aborts unless ``--allow-root`` is given: root is unnecessary for normal
operation, breaks access to the user's session bus, and makes every mistake
more expensive. And the single-instance lock is taken only by the modes that
can send input, so a read-only watcher can always be started alongside.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import signal
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from agent_watch import doctor as doctor_module
from agent_watch.config import (
    Config,
    ConfigError,
    Mode,
    default_config_path,
    describe,
    load,
)
from agent_watch.fsm import Observation, Supervisor, SystemInspector
from agent_watch.lock import LockHeldError, SingleInstanceLock
from agent_watch.logging_setup import setup
from agent_watch.picker import Candidate, NumberedPicker, discover, pick_with_fzf
from agent_watch.policy import Decision
from agent_watch.quota import default_sources
from agent_watch.state_store import StateStore
from agent_watch.terminal.konsole import KonsoleAdapter
from agent_watch.ui import render_line, render_status
from agent_watch.version import __version__

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 130

ROOT_WARNING = """\
WARNING: agent-watch should run as your KDE desktop user, not as root.

Running as root can break access to the user's D-Bus session, change the
environment the agents were started with, and makes an incorrect keystroke more
expensive. Re-run without sudo, or pass --allow-root if you know why you want
this.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-watch",
        description=(
            "Supervise Codex CLI and Claude Code sessions in KDE Konsole and resume "
            "them safely once a usage window resets."
        ),
    )
    parser.add_argument("--version", action="version", version=f"agent-watch {__version__}")
    parser.add_argument("--config", type=Path, default=None, help="path to the config file")
    parser.add_argument("--log-file", type=Path, default=None, help="override the log file")
    parser.add_argument(
        "--allow-root", action="store_true", help="permit running as root (diagnostics only)"
    )
    parser.add_argument("--verbose", action="store_true", help="also log to stderr")

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="watch selected sessions (default)")
    modes = run_parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--observe", action="store_true", help="never send input; report what would happen"
    )
    modes.add_argument("--ask", action="store_true", help="ask before resuming a session")
    modes.add_argument("--auto", action="store_true", help="resume automatically where permitted")
    run_parser.add_argument(
        "--reset-grace", default=None, help="extra wait after a reset, e.g. 90s"
    )
    run_parser.add_argument("--scan-interval", default=None, help="terminal scan interval")
    run_parser.add_argument(
        "--all", action="store_true", help="watch every detected agent without prompting"
    )
    run_parser.add_argument(
        "--once", action="store_true", help="run a single tick and exit (useful in scripts)"
    )
    run_parser.add_argument(
        "--no-fzf", action="store_true", help="never use fzf even when it is installed"
    )

    subparsers.add_parser("status", help="list Konsole sessions and how they classify")
    subparsers.add_parser("doctor", help="check whether this environment is supported")
    subparsers.add_parser("init", help="write a default config file")
    subparsers.add_parser("config", help="show the effective configuration")

    logs_parser = subparsers.add_parser("logs", help="show the event log")
    logs_parser.add_argument("-n", "--lines", type=int, default=40, help="how many lines to show")

    return parser


def _overrides(args: argparse.Namespace) -> dict[str, str]:
    overrides: dict[str, str] = {}
    if getattr(args, "observe", False):
        overrides["MODE"] = Mode.OBSERVE.value
    elif getattr(args, "ask", False):
        overrides["MODE"] = Mode.ASK.value
    elif getattr(args, "auto", False):
        overrides["MODE"] = Mode.AUTO.value
    if getattr(args, "reset_grace", None):
        overrides["RESET_GRACE"] = args.reset_grace
    if getattr(args, "scan_interval", None):
        overrides["SCAN_INTERVAL"] = args.scan_interval
    if args.log_file is not None:
        overrides["LOG_FILE"] = str(args.log_file)
    if args.allow_root:
        overrides["ALLOW_ROOT"] = "true"
    if getattr(args, "no_fzf", False):
        overrides["USE_FZF"] = "false"
    return overrides


def _check_privileges(config: Config, stream) -> bool:
    if os.geteuid() != 0 or config.allow_root:
        return True
    stream.write(ROOT_WARNING)
    return False


def _select_sessions(
    config: Config,
    candidates: list[Candidate],
    *,
    watch_all: bool,
    stream,
    reader: Callable[[str], str],
) -> list[Candidate] | None:
    if watch_all:
        return [candidate for candidate in candidates if candidate.eligible]
    if config.use_fzf:
        chosen = pick_with_fzf(candidates)
        if chosen is not None:
            return chosen
    picker = NumberedPicker(read=reader, write=lambda text: stream.write(text + "\n"))
    return picker.run(candidates)


def _confirmer(stream, reader):
    def confirm(observation: Observation, decision: Decision) -> bool:
        action = decision.action
        keys = action.kind.value if action else "?"
        stream.write(
            f"\n{observation.recognition.provider if observation.recognition else '?'} "
            f"{observation.ref.session_id} is blocked and usage looks available again.\n"
            f"Send {keys} to resume it? [y/N] "
        )
        stream.flush()
        try:
            answer = reader("").strip().lower()
        except EOFError:
            # No one is there to answer, and silence is not a yes.
            return False
        return answer in {"y", "yes"}

    return confirm


def _build_supervisor(config: Config, args: argparse.Namespace, stream, reader) -> Supervisor:
    log = setup(config.resolved_log_file(), to_stderr=args.verbose)
    return Supervisor(
        terminal=KonsoleAdapter(),
        config=config,
        store=StateStore.in_directory(config.resolved_state_dir()).load(),
        quota_sources=default_sources(config.resolved_state_dir()),
        log=log,
        inspector=SystemInspector(),
        confirm=_confirmer(stream, reader) if config.mode is Mode.ASK else None,
    )


def command_run(
    config: Config, args: argparse.Namespace, stream, reader: Callable[[str], str]
) -> int:
    if not _check_privileges(config, stream):
        return EXIT_ERROR

    supervisor = _build_supervisor(config, args, stream, reader)
    inspector = SystemInspector()
    candidates = discover(supervisor.terminal, inspector)
    if not candidates:
        stream.write("No Konsole sessions found. Run 'agent-watch doctor' for details.\n")
        return EXIT_ERROR

    chosen = _select_sessions(config, candidates, watch_all=args.all, stream=stream, reader=reader)
    if chosen is None:
        stream.write("Nothing selected.\n")
        return EXIT_OK
    for candidate in chosen:
        if candidate.info is None or candidate.provider is None:  # pragma: no cover - guarded
            continue
        supervisor.select(
            candidate.session.ref,
            candidate.info.identity,
            candidate.provider,
            candidate.session.title,
        )
    if not supervisor.sessions:
        stream.write("Nothing selected.\n")
        return EXIT_OK

    # Only a mode that can type needs to exclude a second instance.
    lock = SingleInstanceLock.in_directory(config.resolved_runtime_dir())
    if config.mode.may_send_input:
        try:
            lock.acquire()
        except LockHeldError:
            stream.write(
                "Another agent-watch is already running. Only one instance may send "
                "input; use --observe to watch read-only.\n"
            )
            return EXIT_ERROR
    try:
        return _loop(supervisor, config, args, stream)
    finally:
        lock.release()


def _loop(supervisor: Supervisor, config: Config, args: argparse.Namespace, stream) -> int:
    stop = {"requested": False}

    def request_stop(signum, frame) -> None:  # pragma: no cover - signal path
        stop["requested"] = True

    for received in (signal.SIGINT, signal.SIGTERM):
        # Not the main thread: there is nothing to install, and nothing to do.
        with contextlib.suppress(ValueError):
            signal.signal(received, request_stop)

    last_event = ""
    while not stop["requested"]:
        supervisor.prune_and_rebind()
        decisions = supervisor.tick()
        now = datetime.now(UTC)
        if config.mode is Mode.OBSERVE:
            for session in supervisor.sessions.values():
                stream.write(render_line(session, now) + "\n")
        else:
            last_event = _summarise(supervisor.sessions.values(), decisions) or last_event
            stream.write(
                render_status(
                    supervisor.sessions.values(), now=now, config=config, last_event=last_event
                )
                + "\n"
            )
        stream.flush()
        if args.once:
            return EXIT_OK
        time.sleep(config.scan_interval)
    return EXIT_INTERRUPTED


def _summarise(sessions, decisions: Sequence[Decision]) -> str:
    for session, decision in zip(sessions, decisions, strict=False):
        if decision.allowed:
            return f"{session.provider_name} {session.ref.session_id}: {decision.reason}"
    return ""


def command_status(config: Config, stream) -> int:
    adapter = KonsoleAdapter()
    if not adapter.is_available():
        stream.write("Konsole D-Bus is not reachable. Run 'agent-watch doctor'.\n")
        return EXIT_ERROR
    candidates = discover(adapter, SystemInspector())
    if not candidates:
        stream.write("No Konsole sessions found.\n")
        return EXIT_OK
    for candidate in candidates:
        note = f"  ({candidate.note})" if candidate.note else ""
        stream.write(
            f"{candidate.label:<10} {candidate.tty:<8} PID {candidate.session.foreground_pid:<8} "
            f"{candidate.cwd}{note}\n"
        )
    return EXIT_OK


def command_doctor(config: Config, stream) -> int:
    checks = doctor_module.run(config)
    stream.write(doctor_module.render(checks) + "\n")
    return doctor_module.exit_code(checks)


DEFAULT_CONFIG_TEMPLATE = """\
# agent-watch configuration. Parsed as KEY=VALUE; never executed.

# observe | ask | auto
MODE=ask

SCAN_INTERVAL=2s
USAGE_POLL_INTERVAL=60s

# Extra wait after the provider's nominal reset, because a reset timestamp can
# pass while usage is not yet actually available.
RESET_GRACE=60s

MAX_RESUME_ATTEMPTS=3
RETRY_DELAYS=5s 30s 60s

# Nothing below costs money or changes model quality unless you turn it on.
RESUME_AFTER_RESET=true
AUTO_ACCEPT_MODEL_DOWNGRADE=false
AUTO_USE_PAID_CREDITS=false
AUTO_BUY_CREDITS=false
AUTO_CONSUME_RESET_CREDIT=false

# Claude resumes with a bare Enter on an explicit affordance. Codex has no such
# affordance: resuming it means typing into the composer, so it is opt-in.
ALLOW_CODEX_AUTO_RESUME=false
"""


def command_init(config: Config, args: argparse.Namespace, stream) -> int:
    path = args.config or default_config_path()
    if path.exists():
        stream.write(f"{path} already exists; leaving it alone.\n")
        return EXIT_OK
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
    stream.write(f"Wrote {path}\n")
    return EXIT_OK


def command_config(config: Config, stream) -> int:
    for key, value in describe(config):
        stream.write(f"{key:<28} {value}\n")
    return EXIT_OK


def command_logs(config: Config, args: argparse.Namespace, stream) -> int:
    path = config.resolved_log_file()
    if not path.is_file():
        stream.write(f"No log at {path} yet.\n")
        return EXIT_OK
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-args.lines :]:
        stream.write(line + "\n")
    return EXIT_OK


def main(
    argv: Sequence[str] | None = None,
    *,
    stream=None,
    reader: Callable[[str], str] = input,
) -> int:
    parser = build_parser()
    arguments = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(arguments)
    if args.command is None:
        # Running bare means running; re-parse so `run`'s own defaults exist.
        args = parser.parse_args([*arguments, "run"])
    out = stream if stream is not None else sys.stdout

    try:
        config = load(config_path=args.config, overrides=_overrides(args))
    except ConfigError as exc:
        out.write(f"Configuration error: {exc}\n")
        return EXIT_ERROR

    if args.command == "run":
        return command_run(config, args, out, reader)
    if args.command == "status":
        return command_status(config, out)
    if args.command == "doctor":
        return command_doctor(config, out)
    if args.command == "init":
        return command_init(config, args, out)
    if args.command == "config":
        return command_config(config, out)
    if args.command == "logs":
        return command_logs(config, args, out)
    parser.print_help(out)  # pragma: no cover - argparse covers the known set
    return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
