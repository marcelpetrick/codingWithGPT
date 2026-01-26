"""
main.py - Review files touched in the last local Git commit using an Ollama server.

Supports:
- --directory="foo/bar/"  -> limits processing to that subdirectory (relative or absolute)
- Finds Git repo root starting from --directory (or CWD if omitted)
- Runs Git commands against the detected repo root
- Sanitizes Git-provided paths to prevent traversal / repo-escape
- Ollama HTTP timeouts + retries + verbose logging

Usage examples:
  python3 main.py
  python3 main.py --directory="ownCodeReview"
  python3 main.py --directory="/home/user/repos/myrepo/src"
  python3 main.py --directory="foo/bar" --v > review.md
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import random
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List, Optional, Tuple


REVIEW_PROMPT = """\
Act as an expert reviewer for GCC-built C++/Qt (QML) on embedded + desktop Linux. I will paste C++/QML/CMake/qmake. Find critical failures: runtime crashes/UB, deadlocks, QObject ownership bugs, QML binding loops/null access, plugin/module loading failures, and cross-compilation/deployment breakages.

Return:

Top 5 critical issues (ranked) with exact fixes.

Be direct; include corrected snippets.
"""

DEFAULT_HOST = "http://192.168.100.32:11434"
TAGS_PATH = "/api/tags"
GENERATE_PATH = "/api/generate"
DEFAULT_MAX_CHARS_PER_FILE = 60_000


@dataclass(frozen=True)
class HttpConfig:
    timeout_s: int = 900
    retries: int = 4
    backoff_base_s: float = 0.6
    backoff_max_s: float = 8.0
    jitter_s: float = 0.25


class UnsafePathError(RuntimeError):
    pass


def log(msg: str, verbose: bool) -> None:
    if verbose:
        sys.stderr.write(msg.rstrip() + "\n")
        sys.stderr.flush()


# -----------------------------
# Git handling
# -----------------------------
def ensure_git_available(verbose: bool) -> None:
    git_path = shutil.which("git")
    if not git_path:
        raise RuntimeError("git is not installed or not on PATH.")
    log(f"[git] Found git at: {git_path}", verbose)
    try:
        p = subprocess.run(
            ["git", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        log(f"[git] {p.stdout.strip()}", verbose)
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or "").strip()
        raise RuntimeError(f"git exists but failed to run 'git --version'. {msg}".strip())


def run_git(args: List[str], cwd: str, verbose: bool = False) -> str:
    """
    Run git with -C <cwd> and return stdout.
    """
    cmd = ["git", "-C", cwd] + args
    log(f"[git] {' '.join(cmd)}", verbose)
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return p.stdout
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        stdout = (e.stdout or "").strip()
        details = stderr or stdout or str(e)
        raise RuntimeError(f"git command failed: git {' '.join(args)}\n{details}".strip())


def find_repo_root(start_dir: str, verbose: bool) -> str:
    """
    Find Git repo root for a given directory by running:
      git -C <start_dir> rev-parse --show-toplevel
    """
    try:
        root = run_git(["rev-parse", "--show-toplevel"], cwd=start_dir, verbose=verbose).strip()
    except RuntimeError as e:
        raise RuntimeError(
            f"Unable to find a Git repository starting from: {start_dir}\n{e}"
        ) from e

    if not root:
        raise RuntimeError("git rev-parse --show-toplevel returned empty.")
    return root


def last_commit_info(repo_root: str, verbose: bool) -> Tuple[str, str, str]:
    sha = run_git(["rev-parse", "HEAD"], cwd=repo_root, verbose=verbose).strip()
    subject = run_git(["log", "-1", "--pretty=%s"], cwd=repo_root, verbose=verbose).strip()
    date_iso = run_git(["log", "-1", "--pretty=%cI"], cwd=repo_root, verbose=verbose).strip()
    return sha, subject, date_iso


def files_touched_in_last_commit(repo_root: str, verbose: bool) -> List[str]:
    out = run_git(["show", "--name-only", "--pretty=", "HEAD"], cwd=repo_root, verbose=verbose)
    files = [line.strip() for line in out.splitlines() if line.strip()]

    # Deduplicate preserving order
    seen = set()
    unique: List[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


# -----------------------------
# Path safety & directory filtering
# -----------------------------
def _is_within_dir(candidate: str, root: str) -> bool:
    root_real = os.path.realpath(root)
    cand_real = os.path.realpath(candidate)
    try:
        common = os.path.commonpath([root_real, cand_real])
    except ValueError:
        return False
    return common == root_real


def safe_resolve_repo_path(repo_root_path: str, path_rel: str) -> str:
    if not path_rel or path_rel.strip() == "":
        raise UnsafePathError("Empty path from Git output.")

    norm = os.path.normpath(path_rel)

    if os.path.isabs(norm):
        raise UnsafePathError(f"Absolute paths are not allowed: {path_rel}")

    drive, _ = os.path.splitdrive(norm)
    if drive:
        raise UnsafePathError(f"Drive-letter paths are not allowed: {path_rel}")
    if norm.startswith("\\\\"):
        raise UnsafePathError(f"UNC paths are not allowed: {path_rel}")

    parts = norm.split(os.sep)
    if any(part == ".." for part in parts):
        raise UnsafePathError(f"Path traversal is not allowed: {path_rel}")

    abs_path = os.path.abspath(os.path.join(repo_root_path, norm))

    if not _is_within_dir(abs_path, repo_root_path):
        raise UnsafePathError(f"Resolved path escapes repo root: {path_rel}")

    return abs_path


def normalize_repo_relative_dir(repo_root: str, directory: str) -> str:
    """
    Convert user-provided directory (abs or relative) to a normalized *repo-relative* prefix.

    Returns:
      ""            -> means repo root (no filtering)
      "foo/bar"     -> filter to this subtree
    """
    d_abs = os.path.abspath(directory)
    repo_root_abs = os.path.abspath(repo_root)

    if not _is_within_dir(d_abs, repo_root_abs):
        raise RuntimeError(
            f"--directory must be inside the git repo.\n"
            f"Repo root: {repo_root_abs}\n"
            f"Directory: {d_abs}"
        )

    rel = os.path.relpath(d_abs, repo_root_abs)
    rel_norm = "" if rel in (".", "") else rel.replace(os.sep, "/").rstrip("/")

    return rel_norm


def filter_files_by_directory(files_rel: List[str], dir_rel_prefix: str) -> List[str]:
    """
    dir_rel_prefix is repo-relative using forward slashes, no trailing slash, or "" for no filter.
    """
    if not dir_rel_prefix:
        return files_rel

    prefix = dir_rel_prefix + "/"
    out: List[str] = []
    for f in files_rel:
        f_norm = f.replace("\\", "/")
        if f_norm == dir_rel_prefix or f_norm.startswith(prefix):
            out.append(f)
    return out


# -----------------------------
# File IO
# -----------------------------
def is_text_file(path: str) -> bool:
    try:
        with open(path, "rb") as fp:
            chunk = fp.read(4096)
        return b"\x00" not in chunk
    except OSError:
        return False


def read_file_working_tree(path: str, max_chars: int) -> Tuple[str, bool]:
    with open(path, "rb") as fp:
        raw = fp.read()

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")

    if len(text) > max_chars:
        return text[:max_chars], True
    return text, False


# -----------------------------
# Ollama communication (timeouts + retries)
# -----------------------------
def _sleep_backoff(attempt: int, cfg: HttpConfig, verbose: bool, context: str) -> None:
    base = cfg.backoff_base_s * (2 ** (attempt - 1))
    delay = min(cfg.backoff_max_s, base) + random.uniform(0, cfg.jitter_s)
    log(f"[retry] {context}: sleeping {delay:.2f}s before retry #{attempt + 1}", verbose)
    time.sleep(delay)


def http_json(
    url: str,
    payload: Optional[dict] = None,
    cfg: Optional[HttpConfig] = None,
    verbose: bool = False,
) -> dict:
    if cfg is None:
        cfg = HttpConfig()

    last_err: Optional[Exception] = None

    for attempt in range(0, cfg.retries + 1):
        try:
            if payload is None:
                req = urllib.request.Request(url, method="GET")
                log(f"[http] GET {url}", verbose)
            else:
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data_bytes,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                log(f"[http] POST {url} (json {len(data_bytes)} bytes)", verbose)

            with urllib.request.urlopen(req, timeout=cfg.timeout_s) as resp:
                body = resp.read().decode("utf-8")
                status = getattr(resp, "status", 200)
                log(f"[http] {url} -> HTTP {status} ({len(body)} chars)", verbose)
                return json.loads(body) if body else {}

        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass

            status = e.code
            msg = f"HTTP {status} calling {url}"
            if body:
                msg += f"\n{body}"

            if status >= 500 or status == 429:
                last_err = RuntimeError(msg.strip())
                log(f"[http] transient error: {msg.strip().splitlines()[0]}", verbose)
                if attempt < cfg.retries:
                    _sleep_backoff(attempt + 1, cfg, verbose, context=f"{url} (HTTP {status})")
                    continue
                raise last_err

            raise RuntimeError(msg.strip())

        except urllib.error.URLError as e:
            last_err = RuntimeError(f"Network error calling {url}: {e}")
            log(f"[http] network error: {e}", verbose)
            if attempt < cfg.retries:
                _sleep_backoff(attempt + 1, cfg, verbose, context=f"{url} (network)")
                continue
            raise last_err

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON from {url}: {e}")

    raise RuntimeError(f"HTTP request failed after retries: {last_err}")


def pick_model(host: str, explicit_model: Optional[str], http_cfg: HttpConfig, verbose: bool) -> str:
    if explicit_model:
        log(f"[ollama] Using explicit model: {explicit_model}", verbose)
        return explicit_model

    env_model = os.environ.get("OLLAMA_MODEL", "").strip()
    if env_model:
        log(f"[ollama] Using model from OLLAMA_MODEL: {env_model}", verbose)
        return env_model

    tags_url = host.rstrip("/") + TAGS_PATH
    data = http_json(tags_url, payload=None, cfg=http_cfg, verbose=verbose)
    models = data.get("models") or []
    if not models:
        raise RuntimeError(
            f"No models found at {tags_url}. "
            "Pull a model on the Ollama server and retry."
        )

    first = models[0]
    name = first.get("name")
    if not name:
        raise RuntimeError(f"Unexpected /api/tags response format: {data}")

    log(f"[ollama] Auto-selected model from /api/tags: {name}", verbose)
    return name


def ollama_generate(host: str, model: str, prompt: str, http_cfg: HttpConfig, verbose: bool) -> str:
    url = host.rstrip("/") + GENERATE_PATH
    payload = {"model": model, "prompt": prompt, "stream": False}
    log(f"[ollama] Generating model={model} prompt_chars={len(prompt)}", verbose)
    data = http_json(url, payload=payload, cfg=http_cfg, verbose=verbose)
    resp = data.get("response")
    if resp is None:
        raise RuntimeError(f"Unexpected /api/generate response: {json.dumps(data)[:2000]}")
    return str(resp)


# -----------------------------
# Markdown formatting
# -----------------------------
def format_md_header(title: str, level: int = 2) -> str:
    return f"{'#' * level} {title}\n"


def build_file_prompt(path_rel: str, content: str, truncated: bool) -> str:
    trunc_note = ""
    if truncated:
        trunc_note = (
            "\n\nNOTE: File content was truncated before review due to size limits. "
            "If you want full-file review, increase --max-chars.\n"
        )

    ext = os.path.splitext(path_rel)[1].lower()
    lang = {
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".c": "c",
        ".h": "cpp",
        ".hpp": "cpp",
        ".hh": "cpp",
        ".hxx": "cpp",
        ".qml": "qml",
        ".cmake": "cmake",
        ".txt": "",
        ".md": "markdown",
        ".pro": "",
        ".pri": "",
        ".qrc": "xml",
        ".ui": "xml",
        ".qbs": "",
        ".py": "python",
        ".sh": "bash",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".xml": "xml",
    }.get(ext, "")

    return (
        REVIEW_PROMPT
        + f"\n\nFile: {path_rel}\n"
        + trunc_note
        + f"\n```{lang}\n{content}\n```\n"
    )


# -----------------------------
# Main
# -----------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Review files touched in last Git commit using Ollama; output Markdown.")
    ap.add_argument("--directory", default=".", help="Directory to run from / limit processing to (default: '.')")
    ap.add_argument("--host", default=DEFAULT_HOST, help=f"Ollama host base URL (default: {DEFAULT_HOST})")
    ap.add_argument("--model", default=None, help="Ollama model name (default: first from /api/tags or $OLLAMA_MODEL)")
    ap.add_argument("--out", default=None, help="Write Markdown report to this file (default: stdout)")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS_PER_FILE, help="Max characters to send per file")
    ap.add_argument("--include-nontext", action="store_true", help="Attempt to send non-text files too (default: skip)")
    ap.add_argument("--v", action="store_true", help="Verbose: print progress/actions to stderr")

    # Ollama retry/timeout knobs
    ap.add_argument("--timeout", type=int, default=900, help="HTTP timeout seconds per request (default: 900)")
    ap.add_argument("--retries", type=int, default=4, help="HTTP retries for transient Ollama errors (default: 4)")
    ap.add_argument("--backoff-base", type=float, default=0.6, help="Backoff base seconds (default: 0.6)")
    ap.add_argument("--backoff-max", type=float, default=8.0, help="Backoff max seconds (default: 8.0)")
    ap.add_argument("--jitter", type=float, default=0.25, help="Backoff jitter seconds (default: 0.25)")

    args = ap.parse_args()
    verbose = bool(args.v)

    http_cfg = HttpConfig(
        timeout_s=int(args.timeout),
        retries=int(args.retries),
        backoff_base_s=float(args.backoff_base),
        backoff_max_s=float(args.backoff_max),
        jitter_s=float(args.jitter),
    )

    ensure_git_available(verbose)

    dir_abs = os.path.abspath(args.directory)
    if not os.path.isdir(dir_abs):
        raise RuntimeError(f"--directory is not a directory or does not exist: {dir_abs}")

    log(f"[init] Start directory: {dir_abs}", verbose)

    # Find repo root based on the provided directory (requested)
    root = find_repo_root(dir_abs, verbose)
    log(f"[init] Repo root: {root}", verbose)

    # Directory filter prefix (repo-relative)
    dir_rel_prefix = normalize_repo_relative_dir(root, dir_abs)
    log(f"[init] Directory filter (repo-relative): '{dir_rel_prefix or '(repo root)'}'", verbose)

    commit_sha, commit_subject, commit_date = last_commit_info(root, verbose)
    files_rel_all = files_touched_in_last_commit(root, verbose)
    files_rel = filter_files_by_directory(files_rel_all, dir_rel_prefix)

    log(f"[git] HEAD: {commit_sha}", verbose)
    log(f"[git] Files touched in HEAD (all): {len(files_rel_all)}", verbose)
    log(f"[git] Files after --directory filter: {len(files_rel)}", verbose)

    model = pick_model(args.host, args.model, http_cfg=http_cfg, verbose=verbose)

    now = _dt.datetime.now().isoformat(timespec="seconds")
    md_parts: List[str] = []
    md_parts.append("# C++/Qt Change Review (Last Commit)\n")
    md_parts.append(f"- Repo: `{root}`\n")
    md_parts.append(f"- Commit: `{commit_sha}`\n")
    md_parts.append(f"- Subject: {commit_subject}\n")
    md_parts.append(f"- Commit date: {commit_date}\n")
    md_parts.append(f"- Generated: {now}\n")
    md_parts.append(f"- Directory filter: `{dir_rel_prefix or '.'}`\n")
    md_parts.append(f"- Ollama host: `{args.host}`\n")
    md_parts.append(f"- Model: `{model}`\n")
    md_parts.append("\n---\n\n")

    if not files_rel:
        md_parts.append(
            "No files found in the last commit within the selected directory filter.\n"
        )
        report = "".join(md_parts)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fp:
                fp.write(report)
            log(f"[out] Wrote report to {args.out}", verbose)
        else:
            sys.stdout.write(report)
        return 0

    md_parts.append(format_md_header("Files Reviewed", level=2))
    for f in files_rel:
        md_parts.append(f"- `{f}`\n")
    md_parts.append("\n---\n\n")

    for i, path_rel in enumerate(files_rel, start=1):
        md_parts.append(format_md_header(f"{i}. {path_rel}", level=2))
        log(f"[file] #{i} relative={path_rel}", verbose)

        try:
            abs_path = safe_resolve_repo_path(root, path_rel)
            log(f"[file] #{i} resolved={abs_path}", verbose)
        except UnsafePathError as e:
            md_parts.append(
                textwrap.dedent(
                    f"""\
                    **Skipped:** unsafe path from Git.

                    - Path: `{path_rel}`
                    - Reason: {e}

                    ---
                    """
                )
                + "\n"
            )
            log(f"[file] #{i} SKIP unsafe path: {e}", verbose)
            continue

        if not os.path.exists(abs_path):
            md_parts.append(
                textwrap.dedent(
                    f"""\
                    **Skipped:** file not present in working tree.

                    - Relative: `{path_rel}`
                    - Absolute checked: `{abs_path}`

                    ---
                    """
                )
                + "\n"
            )
            log(f"[file] #{i} SKIP missing on disk", verbose)
            continue

        if (not args.include_nontext) and (not is_text_file(abs_path)):
            md_parts.append("**Skipped:** detected as binary/non-text file.\n\n---\n\n")
            log(f"[file] #{i} SKIP binary/non-text", verbose)
            continue

        try:
            content, truncated = read_file_working_tree(abs_path, args.max_chars)
            log(f"[file] #{i} read chars={len(content)} truncated={truncated}", verbose)
        except OSError as e:
            md_parts.append(f"**Error reading file:** `{e}`\n\n---\n\n")
            log(f"[file] #{i} ERROR reading: {e}", verbose)
            continue

        prompt = build_file_prompt(path_rel, content, truncated)

        try:
            log(f"[ollama] #{i} /api/generate ...", verbose)
            resp = ollama_generate(args.host, model, prompt, http_cfg=http_cfg, verbose=verbose)
            log(f"[ollama] #{i} response chars={len(resp)}", verbose)
        except Exception as e:
            md_parts.append(f"**Ollama error:** {e}\n\n---\n\n")
            log(f"[ollama] #{i} ERROR: {e}", verbose)
            continue

        md_parts.append(resp.strip() + "\n\n---\n\n")

    report = "".join(md_parts)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fp:
            fp.write(report)
        log(f"[out] Wrote report to {args.out}", verbose)
    else:
        sys.stdout.write(report)
        log("[out] Wrote report to stdout", verbose)

    log("[done] Completed", verbose)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        raise SystemExit(2)
