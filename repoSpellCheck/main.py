#!/usr/bin/env python3
"""
main.py — Clone a GitHub repo, run codespell, report changes, and clean up.

Usage (default shape you requested):
    python3 main.py repo=github.com/marceleptrick/notes path=.

Optional knobs (secure, no shell injection; all values are parsed as key=value):
    branch=main          # checkout a specific branch
    depth=1              # shallow clone depth (default: 1)
    keep=false           # keep the temp clone (default: false); useful for debugging
    keep_on_error=true   # preserve temp dir if something fails (default: true)
    save_json=out.json   # write machine-readable summary
    codespell="..."      # override the codespell command (default is provided below)

Security & safety notes:
- No shell=True anywhere.
- All external commands use argument lists (subprocess + shlex) to avoid injection.
- Repository URL is normalized to HTTPS and constrained to GitHub.
- Temporary directory is created under the provided working path and removed afterward (unless keep=true).
"""

from __future__ import annotations

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

# --------------------------- UI helpers ---------------------------

def _supports_color() -> bool:
    return sys.stdout.isatty()

if _supports_color():
    BOLD = "\033[1m"; DIM = "\033[2m"; OK = "\033[92m"; WARN = "\033[93m"; ERR = "\033[91m"; RESET = "\033[0m"
else:
    BOLD = DIM = OK = WARN = ERR = RESET = ""

def log(section: str, msg: str = "", *, color: str = "", bullet: str = "•") -> None:
    """Structured, chatty logging."""
    prefix = f"{BOLD}{section}{RESET}" if section else ""
    color = color or ""
    if section and msg:
        print(f"{prefix} {color}{msg}{RESET}")
    elif section:
        print(prefix)
    else:
        print(f"{color}{bullet} {msg}{RESET}")

def show_cmd(cmd: List[str]) -> str:
    """Pretty-print a command safely."""
    return " ".join(shlex.quote(p) for p in cmd)

# --------------------------- Data models ---------------------------

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

def parse_keyvals(argv: List[str]) -> Dict[str, str]:
    """
    Accept CLI args as key=value pairs (and boolean flags).
    Example:
      repo=github.com/user/repo path=. branch=main depth=1 keep=false
    """
    args: Dict[str, str] = {}
    for a in argv:
        if "=" in a:
            k, v = a.split("=", 1)
            args[k.strip().lstrip("-").lower()] = v.strip()
        else:
            # allow bare flags like --keep
            k = a.strip().lstrip("-").lower()
            if k:
                args[k] = "true"
    return args

def boolish(v: Optional[str], default: bool = False) -> bool:
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}

# --------------------------- Repo URL handling ---------------------------

_GH_HOST_RE = re.compile(r"^(https://)?(www\.)?github\.com/[^/]+/[^/]+/?(\.git)?$", re.IGNORECASE)
_SSH_GH_RE = re.compile(r"^git@github\.com:[^/]+/[^/]+(?:\.git)?$", re.IGNORECASE)

def normalize_repo_url(repo: str) -> str:
    """
    Normalize accepted GitHub repo identifiers into a safe HTTPS URL ending with .git.

    Accepts:
      github.com/user/repo
      https://github.com/user/repo
      https://github.com/user/repo.git
      git@github.com:user/repo.git

    Returns:
      https://github.com/user/repo.git

    Refuses non-GitHub hosts for safety.
    """
    repo = repo.strip()

    # SSH → HTTPS
    if _SSH_GH_RE.match(repo):
        path = repo.split(":", 1)[1]
        if not path.endswith(".git"):
            path += ".git"
        return f"https://github.com/{path}"

    # Bare github.com path
    if repo.startswith("github.com/"):
        repo = "https://" + repo

    # Ensure HTTPS and .git suffix
    if repo.lower().startswith("https://"):
        # Validate it really is GitHub and shape looks right
        # Normalize trailing slashes
        repo = repo.rstrip("/")
        if not repo.endswith(".git"):
            repo += ".git"
        # Quick safety gate: only allow github.com/<owner>/<repo>.git
        no_git = repo[:-4] if repo.endswith(".git") else repo
        if not _GH_HOST_RE.match(no_git):
            raise ValueError(f"Refusing non-GitHub or malformed repo URL: {repo}")
        return repo

    # Everything else is refused for safety
    raise ValueError(f"Unsupported repo form (only GitHub is allowed): {repo}")

# --------------------------- Subprocess utilities ---------------------------

def ensure_tool_available(executable: str) -> None:
    """Fail fast if a required executable is not on PATH."""
    from shutil import which
    if which(executable) is None:
        raise FileNotFoundError(
            f"Required tool '{executable}' not found in PATH. "
            f"Please install it and try again."
        )

def run_cmd(cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> Tuple[int, str, str]:
    """
    Run a command as a list (never shell=True), stream stdout/stderr lines live,
    and also capture them for later use.
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

    # Stream line-by-line without blocking
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

# --------------------------- Git change inspection ---------------------------

def git_has_changes(cwd: Path) -> bool:
    rc, out, _ = run_cmd(["git", "status", "--porcelain"], cwd=cwd, check=False)
    return rc == 0 and bool(out.strip())

def git_changes_detail(cwd: Path) -> Dict[str, object]:
    detail: Dict[str, object] = {"files": [], "numstat": [], "summary": "", "porcelain": ""}
    _, porcelain, _ = run_cmd(["git", "status", "--porcelain"], cwd=cwd, check=False)
    detail["porcelain"] = porcelain
    _, stat, _ = run_cmd(["git", "diff", "--stat"], cwd=cwd, check=False)
    detail["summary"] = stat
    _, numstat, _ = run_cmd(["git", "diff", "--numstat"], cwd=cwd, check=False)

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
    files = detail.get("files", [])
    numstat = detail.get("numstat", [])

    file_set = {f["file"] for f in files}
    file_set.update({n["file"] for n in numstat})  # type: ignore[index]

    total_added = sum(int(n.get("added", 0)) for n in numstat)  # type: ignore[union-attr]
    total_deleted = sum(int(n.get("deleted", 0)) for n in numstat)  # type: ignore[union-attr]

    status_breakdown: Dict[str, int] = {}
    for f in files:
        status_breakdown[f["status"]] = status_breakdown.get(f["status"], 0) + 1

    return ChangeSummary(
        total_files_changed=len(file_set),
        total_lines_added=total_added,
        total_lines_deleted=total_deleted,
        status_breakdown=status_breakdown,
    )

# --------------------------- Main routine ---------------------------

def main() -> int:
    # Hard default codespell command from your spec (safe, argument-list friendly).
    # You can still override with: codespell="codespell -i 3 -w --interactive 0 --skip='*.json'"
    DEFAULT_CODESPELL = 'codespell -i 3 -w --interactive 0 --skip="*.json"'

    # Parse arguments
    args = parse_keyvals(sys.argv[1:])
    repo_arg = args.get("repo")
    path_arg = args.get("path", ".")
    branch = args.get("branch")
    depth_str = args.get("depth", "1")
    keep = boolish(args.get("keep"), default=False)
    keep_on_error = boolish(args.get("keep_on_error"), default=True)
    save_json = args.get("save_json")
    codespell_arg = args.get("codespell", DEFAULT_CODESPELL)

    # Basic validation
    if not repo_arg:
        print(f"{ERR}ERROR: Missing repo=… argument (e.g., repo=github.com/user/repo).{RESET}", file=sys.stderr)
        return 2
    try:
        depth = max(1, int(depth_str))
    except ValueError:
        print(f"{ERR}ERROR: depth must be an integer ≥ 1 (got: {depth_str}).{RESET}", file=sys.stderr)
        return 2

    # Normalize inputs
    try:
        repo_url = normalize_repo_url(repo_arg)
    except ValueError as e:
        print(f"{ERR}ERROR: {e}{RESET}", file=sys.stderr)
        return 2

    work_root = Path(path_arg).expanduser().resolve()
    if not work_root.exists():
        print(f"{ERR}ERROR: Working path does not exist: {work_root}{RESET}", file=sys.stderr)
        return 2

    # Announce configuration
    log("CONFIG", f"repo: {repo_arg}")
    log("CONFIG", f"normalized clone URL: {repo_url}", color=DIM)
    log("CONFIG", f"working parent path: {work_root}")
    log("CONFIG", f"branch: {branch or '(default)'}")
    log("CONFIG", f"shallow depth: {depth}")
    log("CONFIG", f"keep after run: {keep}")
    log("CONFIG", f"keep on error: {keep_on_error}")
    log("CONFIG", f"codespell command: {codespell_arg}")
    if save_json:
        log("CONFIG", f"save JSON summary: {save_json}")

    # Ensure required tools exist
    try:
        ensure_tool_available("git")
        ensure_tool_available("codespell")
    except FileNotFoundError as e:
        print(f"{ERR}ERROR: {e}{RESET}", file=sys.stderr)
        return 2

    # Prepare run summary
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

    temp_dir: Optional[Path] = None

    # Ctrl-C handling: still attempt cleanup
    interrupted = {"flag": False}
    def _handle_sigint(signum, frame):
        interrupted["flag"] = True
        log("INTERRUPT", "SIGINT received. Attempting clean shutdown…", color=WARN)
    signal.signal(signal.SIGINT, _handle_sigint)

    try:
        # Create isolated temp dir within the working root
        log("STEP", "Creating temporary working directory…", color=OK)
        temp_dir = Path(tempfile.mkdtemp(prefix="codespell-run-", dir=str(work_root)))
        final.clone_dir = str(temp_dir)
        log("", f"Temp dir: {temp_dir}", color=DIM, bullet="→")

        # Clone (shallow, branch optional)
        log("STEP", "Cloning repository (shallow)…", color=OK)
        clone_cmd = ["git", "clone", "--no-tags", f"--depth={depth}"]
        if branch:
            clone_cmd += ["--branch", branch]
        clone_cmd += [repo_url, str(temp_dir)]
        run_cmd(clone_cmd)

        # Verify a clean tree pre-codespell
        log("STEP", "Verifying clean working tree…", color=OK)
        run_cmd(["git", "status", "--porcelain"], cwd=temp_dir)
        run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=temp_dir)

        # Run codespell — parse safely to a list.
        # If caller forgot a path, append '.' to run at repo root.
        log("STEP", "Running codespell…", color=OK)
        cs_args = shlex.split(codespell_arg)
        if not cs_args:
            raise ValueError("codespell command cannot be empty")
        if cs_args[0] != "codespell":
            raise ValueError("codespell command must start with 'codespell'")
        # Ensure a path target is present; if not, add '.'
        if all(not p.startswith(".") and not p.startswith("/") for p in cs_args[1:]):
            cs_args.append(".")

        # Run codespell (non-fatal if it returns non-zero due to findings)
        run_cmd(cs_args, cwd=temp_dir, check=False)

        # Detect changes
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
                    total_files_changed=0, total_lines_added=0, total_lines_deleted=0, status_breakdown={}
                ),
                detail={"files": [], "numstat": [], "summary": "", "porcelain": ""},
            )

        # Present results
        log("RESULT", "Codespell Summary", color=OK)
        if final.had_changes:
            s = final.changes.summary  # type: ignore[union-attr]
            log("", f"Files changed: {s.total_files_changed}")
            log("", f"Lines added: {s.total_lines_added}  |  Lines deleted: {s.total_lines_deleted}")
            if s.status_breakdown:
                log("", "Status breakdown:")
                for k in sorted(s.status_breakdown):
                    log("", f"  {k or '(none)'}: {s.status_breakdown[k]}", bullet="-")

            det = final.changes.detail  # type: ignore[union-attr]
            if det.get("summary", "").strip():
                print()
                print(det["summary"])
            if det.get("files"):
                print()
                log("", "Changed files:", bullet="-")
                for f in det["files"]:  # type: ignore[index]
                    log("", f"  {f['status']:<2} {f['file']}", bullet=" ")
        else:
            log("", "No file changes detected. Working tree remained clean.", color=WARN)

        # Optional JSON output
        if save_json:
            out_path = Path(save_json)
            if not out_path.is_absolute():
                out_path = work_root / out_path
            out_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert dataclasses → dict
            json_payload = asdict(final)
            # Dataclasses nested conversion handled by asdict above.

            with out_path.open("w", encoding="utf-8") as f:
                json.dump(json_payload, f, indent=2)
            log("STEP", f"Saved JSON summary to: {out_path}", color=OK)

        # Graceful end
        return 0

    except Exception as e:
        final.errors = str(e)
        print(f"{ERR}ERROR: {e}{RESET}", file=sys.stderr)
        # Preserve temp dir if desired or on error based on knob
        if temp_dir and (keep or keep_on_error):
            log("CLEANUP", "Preserving temporary directory due to error.", color=WARN)
            print(str(temp_dir))
        else:
            if temp_dir and temp_dir.exists():
                log("CLEANUP", "Removing temporary directory (error).", color=WARN)
                shutil.rmtree(temp_dir, ignore_errors=True)
        return 1

    finally:
        # Normal cleanup (only if not kept)
        if temp_dir and not interrupted["flag"] and not boolish(args.get("keep"), default=False):
            try:
                log("CLEANUP", "Removing temporary directory…", color=OK)
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as ce:
                print(f"{ERR}WARN: Failed to remove temp dir: {ce}{RESET}", file=sys.stderr)

        end_ts = time.time()
        log("DONE", f"Total time: {end_ts - start_ts:.2f}s", color=DIM)

# --------------------------- Entrypoint ---------------------------

if __name__ == "__main__":
    sys.exit(main())
