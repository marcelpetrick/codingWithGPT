#!/usr/bin/env python3
"""
main.py — Clone a GitHub repo, run codespell, report changes, and clean up.

This version adds TWO important behaviors:

1) Parallel codespell runs
   - If your codespell command does NOT already contain explicit target paths,
     we will:
       a) list repository-tracked files via `git ls-files`
       b) split them into chunks
       c) run codespell concurrently on each chunk
   - If your codespell command ALREADY has explicit targets (e.g. `codespell .`
     or `codespell some/file.cs`), we do not override that, and we run it once.

2) Time-bounded runs (per codespell invocation)
   - Each codespell invocation (the single run OR each parallel chunk run)
     is capped by a timeout (default: 10 seconds).
   - If it exceeds the timeout, the process group is killed and we print
     a failure message to the terminal indicating a timeout.

Usage (key=value, like your original):
    python3 main.py repo=https://github.com/marcelpetrick/QtScrobbler path=.

Common options:
    branch=main
    depth=1
    keep=false
    keep_on_error=true
    save_json=out.json
    codespell="codespell -i 3 -w --interactive 0 --skip='*.json'"

Parallel + timeout options:
    timeout=10        # seconds per codespell run (default 10)
    jobs=8            # max number of concurrent codespell processes
    chunk_size=250    # files per chunk. smaller => more chunks => more overhead

Security & safety notes:
- No shell=True anywhere.
- All external commands use argument lists (subprocess + shlex) to avoid injection.
- Repository URL is normalized to HTTPS and constrained to GitHub.
- Temporary directory is created under the provided working path and removed afterward (unless keep* says otherwise).

Tested assumptions:
- Linux-friendly process group killing (start_new_session=True).
- `codespell` is installed and available in PATH.
- `git` is installed and available in PATH.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# --------------------------- Terminal UX helpers ---------------------------
# Keep output readable while still being CI-friendly.
# Color codes are used only when stdout is a TTY.

def _supports_color() -> bool:
    return sys.stdout.isatty()


if _supports_color():
    BOLD = "\033[1m"
    DIM = "\033[2m"
    OK = "\033[92m"
    WARN = "\033[93m"
    ERR = "\033[91m"
    RESET = "\033[0m"
else:
    BOLD = DIM = OK = WARN = ERR = RESET = ""


def log(section: str, msg: str = "", *, color: str = "", bullet: str = "•") -> None:
    """
    Standardized logging:
    - section: a short label (e.g. "STEP", "CONFIG")
    - msg: content
    - color/bullet: optional formatting
    """
    prefix = f"{BOLD}{section}{RESET}" if section else ""
    if section and msg:
        print(f"{prefix} {color}{msg}{RESET}")
    elif section:
        print(prefix)
    else:
        print(f"{color}{bullet} {msg}{RESET}")


def show_cmd(cmd: List[str]) -> str:
    """Render a command list safely for display."""
    return " ".join(shlex.quote(p) for p in cmd)


# --------------------------- Data models for JSON output ---------------------------
# Keeping the structure explicit makes it easier to integrate with CI or other tools.

@dataclass
class ChangeFile:
    file: str
    added: int
    deleted: int


@dataclass
class ChangeSummary:
    total_files_changed: int
    total_lines_added: int
    total_lines_deleted: int
    status_breakdown: Dict[str, int]


@dataclass
class Changes:
    summary: ChangeSummary
    detail: Dict[str, object]


@dataclass
class RunSummary:
    repo: str
    branch: Optional[str]
    started_at: str
    clone_dir: Optional[str]
    codespell_cmd: str
    had_changes: bool
    changes: Optional[Changes]
    errors: Optional[str]


# --------------------------- Argument parsing ---------------------------
# The script intentionally uses simple key=value parsing:
# - safe (no shell eval)
# - easy to use from bash / CI

def parse_keyvals(argv: List[str]) -> Dict[str, str]:
    """
    Parse args like:
      repo=... keep=1 timeout=15
    Also accepts flags like:
      keep
    which become keep=true
    """
    args: Dict[str, str] = {}
    for a in argv:
        if "=" in a:
            k, v = a.split("=", 1)
            args[k.strip().lstrip("-").lower()] = v.strip()
        else:
            k = a.strip().lstrip("-").lower()
            if k:
                args[k] = "true"
    return args


def boolish(v: Optional[str], default: bool = False) -> bool:
    """Parse common truthy values."""
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


def intish(v: Optional[str], default: int) -> int:
    """Parse int with fallback."""
    if v is None:
        return default
    try:
        return int(str(v).strip())
    except ValueError:
        return default


def floatish(v: Optional[str], default: float) -> float:
    """Parse float with fallback."""
    if v is None:
        return default
    try:
        return float(str(v).strip())
    except ValueError:
        return default


# --------------------------- Repo URL handling ---------------------------
# We explicitly constrain to GitHub repos to reduce ambiguity and avoid surprising behavior.

_GH_HOST_RE = re.compile(r"^(https://)?(www\.)?github\.com/[^/]+/[^/]+/?(\.git)?$", re.IGNORECASE)
_SSH_GH_RE = re.compile(r"^git@github\.com:[^/]+/[^/]+(?:\.git)?$", re.IGNORECASE)


def normalize_repo_url(repo: str) -> str:
    """
    Acceptable inputs:
      - github.com/user/repo
      - https://github.com/user/repo
      - https://github.com/user/repo.git
      - git@github.com:user/repo(.git)

    Output:
      - https://github.com/user/repo.git
    """
    repo = repo.strip()

    # Convert SSH form to HTTPS.
    if _SSH_GH_RE.match(repo):
        path = repo.split(":", 1)[1]
        if not path.endswith(".git"):
            path += ".git"
        return f"https://github.com/{path}"

    # If user omits scheme but starts with github.com/.
    if repo.startswith("github.com/"):
        repo = "https://" + repo

    if repo.lower().startswith("https://"):
        repo = repo.rstrip("/")
        # Ensure .git to make cloning consistent.
        if not repo.endswith(".git"):
            repo += ".git"
        # Validate host/path structure (strip .git for matching).
        no_git = repo[:-4] if repo.endswith(".git") else repo
        if not _GH_HOST_RE.match(no_git):
            raise ValueError(f"Refusing non-GitHub or malformed repo URL: {repo}")
        return repo

    raise ValueError(f"Unsupported repo form (only GitHub is allowed): {repo}")


# --------------------------- Subprocess utilities ---------------------------
# Key points:
# - Always use argument lists (never shell=True).
# - `run_cmd_timeboxed` provides timeout killing.
# - `start_new_session=True` allows killing a whole process group.

def ensure_tool_available(executable: str) -> None:
    """Fail early if required executables aren't in PATH."""
    from shutil import which
    if which(executable) is None:
        raise FileNotFoundError(
            f"Required tool '{executable}' not found in PATH. Please install it and try again."
        )


def run_cmd_capture(cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> Tuple[int, str, str]:
    """
    Run a command and capture stdout/stderr (no streaming).
    Useful for programmatic queries (e.g., `git ls-files`).
    """
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd, proc.stdout, proc.stderr)
    return proc.returncode, proc.stdout, proc.stderr


def run_cmd_stream(cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> Tuple[int, str, str]:
    """
    Run a command, stream output live (useful for clone), and capture it too.
    """
    log("", f"$ {show_cmd(cmd)}", color=DIM, bullet="↳")
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    out_chunks: List[str] = []
    err_chunks: List[str] = []

    while True:
        o = proc.stdout.readline() if proc.stdout else ""
        e = proc.stderr.readline() if proc.stderr else ""
        if o:
            print(o.rstrip())
            out_chunks.append(o)
        if e:
            print(f"{DIM}{e.rstrip()}{RESET}", file=sys.stderr)
            err_chunks.append(e)
        if not o and not e and proc.poll() is not None:
            break

    rc = proc.returncode
    out = "".join(out_chunks)
    err = "".join(err_chunks)
    if check and rc != 0:
        raise subprocess.CalledProcessError(rc, cmd, out, err)
    return rc, out, err


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """
    Kill the process group if possible (Linux):
    - We start commands with start_new_session=True, so the child is its own session leader.
    - Killing the process group is the safest way to ensure children are terminated too.
    """
    try:
        pgid = os.getpgid(proc.pid)
    except Exception:
        pgid = None

    try:
        if pgid is not None:
            os.killpg(pgid, signal.SIGKILL)
        else:
            proc.kill()
    except Exception:
        # Best effort fallback.
        try:
            proc.kill()
        except Exception:
            pass


def run_cmd_timeboxed(cmd: List[str], cwd: Optional[Path], timeout_s: float) -> Tuple[int, str, str, bool]:
    """
    Run a command with a hard timeout.
    Returns:
      (rc, stdout, stderr, timed_out)

    Notes:
    - Never raises for non-zero rc; caller decides how to interpret failures.
    - On timeout, kills the entire process group and returns timed_out=True.
    """
    log("", f"$ {show_cmd(cmd)}", color=DIM, bullet="↳")
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,  # <- critical: gives us a killable process group
    )
    try:
        out, err = proc.communicate(timeout=timeout_s)
        return proc.returncode, out or "", err or "", False
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc)
        # try to read whatever got flushed (non-blocking-ish best effort)
        try:
            out, err = proc.communicate(timeout=1)
        except Exception:
            out, err = "", ""
        return 124, out or "", err or "", True


# --------------------------- Git change inspection ---------------------------
# We track changes after codespell to report what got modified.

def git_has_changes(cwd: Path) -> bool:
    """Return True if git working tree has modifications."""
    rc, out, _ = run_cmd_capture(["git", "status", "--porcelain"], cwd=cwd, check=False)
    return rc == 0 and bool(out.strip())


def git_changes_detail(cwd: Path) -> Dict[str, object]:
    """
    Capture:
      - porcelain status
      - diff --stat
      - diff --numstat
    """
    detail: Dict[str, object] = {"files": [], "numstat": [], "summary": "", "porcelain": ""}

    _, porcelain, _ = run_cmd_capture(["git", "status", "--porcelain"], cwd=cwd, check=False)
    detail["porcelain"] = porcelain

    _, stat, _ = run_cmd_capture(["git", "diff", "--stat"], cwd=cwd, check=False)
    detail["summary"] = stat

    _, numstat, _ = run_cmd_capture(["git", "diff", "--numstat"], cwd=cwd, check=False)

    files: List[ChangeFile] = []
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            added, deleted, path = parts
            a = int(added) if added.isdigit() else 0
            d = int(deleted) if deleted.isdigit() else 0
            files.append(ChangeFile(file=path, added=a, deleted=d))
    detail["numstat"] = [asdict(f) for f in files]

    changed_files = []
    for line in porcelain.splitlines():
        status = line[:2].strip()
        path = line[3:].strip() if len(line) > 3 else ""
        if path:
            changed_files.append({"status": status, "file": path})
    detail["files"] = changed_files

    return detail


def summarize_changes(detail: Dict[str, object]) -> ChangeSummary:
    """Summarize the diff for human/CI output."""
    files = detail.get("files", [])
    numstat = detail.get("numstat", [])

    file_set = {f["file"] for f in files}  # type: ignore[index]
    file_set.update({n["file"] for n in numstat})  # type: ignore[index]

    total_added = sum(int(n.get("added", 0)) for n in numstat)  # type: ignore[union-attr]
    total_deleted = sum(int(n.get("deleted", 0)) for n in numstat)  # type: ignore[union-attr]

    status_breakdown: Dict[str, int] = {}
    for f in files:  # type: ignore[assignment]
        status_breakdown[f["status"]] = status_breakdown.get(f["status"], 0) + 1  # type: ignore[index]

    return ChangeSummary(
        total_files_changed=len(file_set),
        total_lines_added=total_added,
        total_lines_deleted=total_deleted,
        status_breakdown=status_breakdown,
    )


# --------------------------- Codespell parallelization ---------------------------
# IMPORTANT: We only parallelize when the codespell command has no explicit targets.
# Why:
# - If user wrote `codespell .` (or a specific folder), they likely know what they want.
# - If we append file lists in that case, we could change semantics.
#
# How we decide "explicit targets":
# - any token after 'codespell' that does not start with '-' is treated as a positional target.
#   Example: 'codespell .' => '.' is an explicit target
#   Example: 'codespell foo/bar.cs' => file is an explicit target
#   Example: 'codespell --skip=*.json' => no explicit target (pure flags)

def _codespell_has_explicit_targets(cs_args: List[str]) -> bool:
    """Heuristic: detect positional targets already in the command."""
    return any((not t.startswith("-")) for t in cs_args[1:])


def _chunk_list(items: List[str], chunk_size: int) -> List[List[str]]:
    """
    Split list into chunks. chunk_size controls granularity:
    - smaller chunk_size -> more chunks -> more overhead but better load balancing
    - larger chunk_size -> fewer chunks -> less overhead
    """
    if chunk_size <= 0:
        chunk_size = 250
    return [items[i: i + chunk_size] for i in range(0, len(items), chunk_size)]


def _run_codespell_worker(
    worker_id: int,
    base_cmd: List[str],
    files: List[str],
    cwd: Path,
    timeout_s: float,
) -> Dict[str, object]:
    """
    Worker unit:
    - execute `codespell ... <files...>` for a chunk
    - enforce the timeout
    - print a clear failure line if timeout happens

    Returns a small dict so the caller can aggregate statuses.
    """
    cmd = base_cmd + files
    rc, out, err, timed_out = run_cmd_timeboxed(cmd, cwd=cwd, timeout_s=timeout_s)

    # Output interleaving can happen with parallel workers.
    # Prefixing each worker line helps reading logs.
    prefix = f"[codespell:{worker_id}] "

    if out.strip():
        for line in out.splitlines():
            print(prefix + line)

    if err.strip():
        for line in err.splitlines():
            print(prefix + line, file=sys.stderr)

    # This is the user-requested behavior:
    # - if it doesn't finish in time, print to command line that it failed
    if timed_out:
        print(f"{ERR}{prefix}FAILED: timed out after {timeout_s:.0f}s (aborted){RESET}")

    return {"worker": worker_id, "rc": rc, "timed_out": timed_out, "files": len(files)}


# --------------------------- Main routine ---------------------------

def main() -> int:
    # Default codespell command:
    # - -w: write fixes
    # - --interactive 0: no prompts (CI-safe)
    # - -i 3: ignore up to 3-character words (common reduction of false positives)
    DEFAULT_CODESPELL = 'codespell -i 3 -w --interactive 0 --skip="*.json"'

    args = parse_keyvals(sys.argv[1:])

    # Required-ish inputs
    repo_arg = args.get("repo")
    path_arg = args.get("path", ".")  # where temp directory is created (parent folder)
    branch = args.get("branch")
    depth_str = args.get("depth", "1")

    # Cleanup behavior
    keep = boolish(args.get("keep"), default=False)
    keep_on_error = boolish(args.get("keep_on_error"), default=True)

    # Output options
    save_json = args.get("save_json")

    # User-specified codespell command string (parsed with shlex.split)
    codespell_arg = args.get("codespell", DEFAULT_CODESPELL)

    # New: timeboxing / parallel knobs
    timeout_s = floatish(args.get("timeout"), default=10.0)   # <-- user can extend window via timeout=...
    jobs = intish(args.get("jobs"), default=(os.cpu_count() or 4))
    chunk_size = intish(args.get("chunk_size"), default=250)

    # Sanitize knobs
    if timeout_s <= 0:
        timeout_s = 10.0
    if jobs <= 0:
        jobs = 1
    if chunk_size <= 0:
        chunk_size = 250

    if not repo_arg:
        print(f"{ERR}ERROR: Missing repo=… argument (e.g., repo=github.com/user/repo).{RESET}", file=sys.stderr)
        return 2

    try:
        depth = max(1, int(depth_str))
    except ValueError:
        print(f"{ERR}ERROR: depth must be an integer ≥ 1 (got: {depth_str}).{RESET}", file=sys.stderr)
        return 2

    try:
        repo_url = normalize_repo_url(repo_arg)
    except ValueError as e:
        print(f"{ERR}ERROR: {e}{RESET}", file=sys.stderr)
        return 2

    work_root = Path(path_arg).expanduser().resolve()
    if not work_root.exists():
        print(f"{ERR}ERROR: Working path does not exist: {work_root}{RESET}", file=sys.stderr)
        return 2

    # Fail fast if tools are missing.
    try:
        ensure_tool_available("git")
        ensure_tool_available("codespell")
    except FileNotFoundError as e:
        print(f"{ERR}ERROR: {e}{RESET}", file=sys.stderr)
        return 2

    # Record run metadata early (useful if failures happen later).
    start_ts = time.time()
    final = RunSummary(
        repo=repo_arg,
        branch=branch,
        started_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_ts)),
        clone_dir=None,
        codespell_cmd=codespell_arg,
        had_changes=False,
        changes=None,
        errors=None,
    )

    log("CONFIG", f"repo: {repo_arg}")
    log("CONFIG", f"normalized clone URL: {repo_url}", color=DIM)
    log("CONFIG", f"working parent path: {work_root}")
    log("CONFIG", f"branch: {branch or '(default)'}")
    log("CONFIG", f"shallow depth: {depth}")
    log("CONFIG", f"keep after run: {keep}")
    log("CONFIG", f"keep on error: {keep_on_error}")
    log("CONFIG", f"codespell command: {codespell_arg}")
    log("CONFIG", f"codespell timeout (per run): {timeout_s:.0f}s")
    log("CONFIG", f"codespell parallel jobs: {jobs}")
    log("CONFIG", f"codespell chunk_size: {chunk_size}")
    if save_json:
        log("CONFIG", f"save JSON summary: {save_json}")

    temp_dir: Optional[Path] = None

    # Handle Ctrl+C nicely:
    # - Mark interrupted, proceed to cleanup decision.
    interrupted = {"flag": False}

    def _handle_sigint(signum, frame):
        interrupted["flag"] = True
        log("INTERRUPT", "SIGINT received. Attempting clean shutdown…", color=WARN)

    signal.signal(signal.SIGINT, _handle_sigint)

    try:
        # Create temp working directory under the given path.
        log("STEP", "Creating temporary working directory…", color=OK)
        temp_dir = Path(tempfile.mkdtemp(prefix="codespell-run-", dir=str(work_root)))
        final.clone_dir = str(temp_dir)
        log("", f"Temp dir: {temp_dir}", color=DIM, bullet="→")

        # Clone
        log("STEP", "Cloning repository (shallow)…", color=OK)
        clone_cmd = ["git", "clone", "--no-tags", f"--depth={depth}"]
        if branch:
            clone_cmd += ["--branch", branch]
        clone_cmd += [repo_url, str(temp_dir)]
        run_cmd_stream(clone_cmd)

        # Basic sanity checks
        log("STEP", "Verifying repository state…", color=OK)
        run_cmd_capture(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=temp_dir, check=True)
        run_cmd_capture(["git", "status", "--porcelain"], cwd=temp_dir, check=True)

        # Parse codespell command with shlex to respect quotes safely.
        # Example:
        #   codespell="codespell -i 3 -w --skip='*.json'"
        cs_args = shlex.split(codespell_arg)
        if not cs_args:
            raise ValueError("codespell command cannot be empty")
        if cs_args[0] != "codespell":
            raise ValueError("codespell command must start with 'codespell'")

        # Decide: run once vs. parallel chunks.
        explicit_targets = _codespell_has_explicit_targets(cs_args)

        log("STEP", "Running codespell…", color=OK)
        if explicit_targets:
            # Respect the user's command; still apply timebox.
            rc, out, err, timed_out = run_cmd_timeboxed(cs_args, cwd=temp_dir, timeout_s=timeout_s)

            if out.strip():
                print(out, end="" if out.endswith("\n") else "\n")
            if err.strip():
                print(err, end="" if err.endswith("\n") else "\n", file=sys.stderr)

            if timed_out:
                # User requested:
                # - abort if not finished within N seconds
                # - print to CLI that it failed
                print(f"{ERR}codespell FAILED: timed out after {timeout_s:.0f}s (aborted){RESET}")
                final.errors = f"codespell timed out after {timeout_s:.0f}s"

            # Non-zero rc can happen due to codespell errors; we don’t hard-fail here,
            # because codespell with -w can still exit non-zero in some scenarios.
            # If you want rc enforcement, add: if rc != 0: final.errors = ...
        else:
            # No explicit targets:
            # - Gather tracked files so we can split them for parallel processing.
            _, files_out, _ = run_cmd_capture(["git", "ls-files"], cwd=temp_dir, check=False)
            files = [f.strip() for f in files_out.splitlines() if f.strip()]

            if not files:
                # If repo has no tracked files (odd), fall back to running on repo root.
                # Still timeboxed.
                fallback = cs_args + ["."]
                rc, out, err, timed_out = run_cmd_timeboxed(fallback, cwd=temp_dir, timeout_s=timeout_s)
                if out.strip():
                    print(out, end="" if out.endswith("\n") else "\n")
                if err.strip():
                    print(err, end="" if err.endswith("\n") else "\n", file=sys.stderr)
                if timed_out:
                    print(f"{ERR}codespell FAILED: timed out after {timeout_s:.0f}s (aborted){RESET}")
                    final.errors = f"codespell timed out after {timeout_s:.0f}s"
            else:
                # Chunk tracked files and run codespell concurrently.
                chunks = _chunk_list(files, chunk_size=chunk_size)
                effective_jobs = min(jobs, len(chunks))

                log(
                    "STEP",
                    f"Parallel codespell: {len(files)} files → {len(chunks)} chunks → {effective_jobs} workers",
                    color=OK,
                )

                # Execute:
                # - Each worker run is independently timeboxed.
                # - If ANY worker times out, we mark the run as failed in final.errors.
                any_timeout = False
                any_worker_fail = False
                results: List[Dict[str, object]] = []

                # ThreadPool is fine because each unit of work is an external process.
                with concurrent.futures.ThreadPoolExecutor(max_workers=effective_jobs) as ex:
                    futures = []
                    for i, chunk in enumerate(chunks, start=1):
                        futures.append(ex.submit(_run_codespell_worker, i, cs_args, chunk, temp_dir, timeout_s))

                    # As futures complete, accumulate their status.
                    for fut in concurrent.futures.as_completed(futures):
                        r = fut.result()
                        results.append(r)
                        if bool(r.get("timed_out")):
                            any_timeout = True
                        # Some users may want to treat non-zero rc as failure too:
                        if int(r.get("rc", 0)) not in (0, 124):
                            any_worker_fail = True

                # Mark errors based on outcomes.
                if any_timeout:
                    final.errors = f"One or more codespell runs timed out (timeout={timeout_s:.0f}s)."
                    log("WARN", "One or more codespell runs timed out; see logs above.", color=WARN)
                elif any_worker_fail:
                    # This is optional behavior; keeping it as a warning-like failure marker
                    # because non-zero rc from codespell can indicate a problem.
                    final.errors = "One or more codespell workers exited non-zero."
                    log("WARN", "One or more codespell workers exited non-zero; see logs above.", color=WARN)

        # After codespell, check if -w changed anything.
        log("STEP", "Checking for changes after codespell…", color=OK)
        had_changes = git_has_changes(temp_dir)
        if had_changes:
            detail = git_changes_detail(temp_dir)
            summary = summarize_changes(detail)
            final.had_changes = True
            final.changes = Changes(summary=summary, detail=detail)
        else:
            final.had_changes = False
            final.changes = Changes(
                summary=ChangeSummary(
                    total_files_changed=0,
                    total_lines_added=0,
                    total_lines_deleted=0,
                    status_breakdown={},
                ),
                detail={"files": [], "numstat": [], "summary": "", "porcelain": ""},
            )

        # Print a concise result summary.
        log("RESULT", "Codespell Summary", color=OK)
        if final.had_changes and final.changes:
            s = final.changes.summary
            log("", f"Files changed: {s.total_files_changed}")
            log("", f"Lines added: {s.total_lines_added}  |  Lines deleted: {s.total_lines_deleted}")
            if s.status_breakdown:
                log("", "Status breakdown:")
                for k in sorted(s.status_breakdown):
                    log("", f"  {k or '(none)'}: {s.status_breakdown[k]}", bullet="-")

            det = final.changes.detail
            if str(det.get("summary", "")).strip():
                print()
                print(det["summary"])
            if det.get("files"):
                print()
                log("", "Changed files:", bullet="-")
                for f in det["files"]:  # type: ignore[index]
                    log("", f"  {f['status']:<2} {f['file']}", bullet=" ")
        else:
            log("", "No file changes detected. Working tree remained clean.", color=WARN)

        # Optional JSON output for machine consumption.
        if save_json:
            out_path = Path(save_json)
            if not out_path.is_absolute():
                out_path = work_root / out_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(asdict(final), f, indent=2)
            log("STEP", f"Saved JSON summary to: {out_path}", color=OK)

        # Exit code convention:
        # - 0: success
        # - 1: codespell timeout or worker failures or other flagged errors
        return 1 if final.errors else 0

    except Exception as e:
        # Anything unexpected ends up here.
        final.errors = str(e)
        print(f"{ERR}ERROR: {e}{RESET}", file=sys.stderr)

        # Keep temp directory for debugging if configured.
        if temp_dir and (keep or keep_on_error):
            log("CLEANUP", "Preserving temporary directory due to error.", color=WARN)
            print(str(temp_dir))
        else:
            if temp_dir and temp_dir.exists():
                log("CLEANUP", "Removing temporary directory (error).", color=WARN)
                shutil.rmtree(temp_dir, ignore_errors=True)
        return 1

    finally:
        # Normal cleanup path (unless user asked to keep).
        if temp_dir and not interrupted["flag"] and not keep:
            try:
                log("CLEANUP", "Removing temporary directory…", color=OK)
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as ce:
                print(f"{ERR}WARN: Failed to remove temp dir: {ce}{RESET}", file=sys.stderr)

        end_ts = time.time()
        log("DONE", f"Total time: {end_ts - start_ts:.2f}s", color=DIM)


if __name__ == "__main__":
    sys.exit(main())
