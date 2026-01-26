#!/usr/bin/env python3
"""
review_last_commit.py

Sequentially reviews files touched in the last local Git commit using an Ollama server.
Outputs a single Markdown report to stdout (or to a file if --out is provided).

Key behaviors:
- "Last local commit" = HEAD
- Touched files: git show --name-only --pretty="" HEAD (paths are relative to repo root)
- File content: read from working tree by default (can be adapted to read exact committed blobs)
- Reviews each file sequentially via Ollama /api/generate
- Output: Markdown

Verbose mode:
- Use --v to print progress and decisions to stderr.

Usage:
  python3 main.py > review.md
  python3 main.py --out review.md
  python3 main.py --model qwen2.5-coder:7b
  python3 main.py --host http://192.168.100.32:11434
  python3 main.py --v
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
from typing import List, Optional, Tuple


REVIEW_PROMPT = """\
Act as an expert reviewer for GCC-built C++/Qt (QML) on embedded + desktop Linux. I will paste C++/QML/CMake/qmake. Find critical failures: runtime crashes/UB, deadlocks, QObject ownership bugs, QML binding loops/null access, plugin/module loading failures, and cross-compilation/deployment breakages.

Return:

Top 10 critical issues (ranked) with exact fixes.

Cross-compile + deployment red flags: sysroot/toolchain, host contamination, pkg-config, install layout, RPATH, Qt plugins/QML imports/qt.conf.

One-hour patch list: smallest changes to reduce crash risk and deployment failures fastest.

Be direct; include corrected snippets.
"""

DEFAULT_HOST = "http://192.168.100.32:11434"
TAGS_PATH = "/api/tags"
GENERATE_PATH = "/api/generate"
DEFAULT_MAX_CHARS_PER_FILE = 60_000


def log(msg: str, verbose: bool) -> None:
    if verbose:
        sys.stderr.write(msg.rstrip() + "\n")
        sys.stderr.flush()


def run_git(args: List[str], verbose: bool = False) -> str:
    """Run a git command in the current working directory and return stdout."""
    cmd = ["git"] + args
    if verbose:
        log(f"[git] {' '.join(cmd)}", True)
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return p.stdout
    except FileNotFoundError:
        raise RuntimeError("git is not installed or not on PATH.")
    except subprocess.CalledProcessError as e:
        msg = e.stderr.strip() or e.stdout.strip() or str(e)
        raise RuntimeError(f"git command failed: git {' '.join(args)}\n{msg}")


def ensure_git_repo(verbose: bool) -> None:
    out = run_git(["rev-parse", "--is-inside-work-tree"], verbose=verbose).strip()
    if out.lower() != "true":
        raise RuntimeError("Current directory is not inside a Git work tree.")


def repo_root(verbose: bool) -> str:
    root = run_git(["rev-parse", "--show-toplevel"], verbose=verbose).strip()
    if not root:
        raise RuntimeError("Unable to determine repo root (git rev-parse --show-toplevel returned empty).")
    return root


def last_commit_info(verbose: bool) -> Tuple[str, str, str]:
    """Return (commit_sha, subject, date_iso)."""
    sha = run_git(["rev-parse", "HEAD"], verbose=verbose).strip()
    subject = run_git(["log", "-1", "--pretty=%s"], verbose=verbose).strip()
    date_iso = run_git(["log", "-1", "--pretty=%cI"], verbose=verbose).strip()
    return sha, subject, date_iso


def files_touched_in_last_commit(verbose: bool) -> List[str]:
    """Files touched in HEAD commit (paths relative to repo root)."""
    out = run_git(["show", "--name-only", "--pretty=", "HEAD"], verbose=verbose)
    files: List[str] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        files.append(line)

    # Deduplicate preserving order
    seen = set()
    unique: List[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)

    return unique


def is_text_file(path: str) -> bool:
    """Heuristic: treat as text unless it contains NUL bytes in the first chunk."""
    try:
        with open(path, "rb") as fp:
            chunk = fp.read(4096)
        return b"\x00" not in chunk
    except OSError:
        return False


def read_file_working_tree(path: str, max_chars: int) -> Tuple[str, bool]:
    """Read file content from working tree. Returns (content, truncated)."""
    with open(path, "rb") as fp:
        raw = fp.read()

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")

    if len(text) > max_chars:
        return text[:max_chars], True
    return text, False


def http_json(url: str, payload: Optional[dict] = None, timeout_s: int = 300, verbose: bool = False) -> dict:
    """Simple JSON HTTP client (stdlib-only)."""
    if payload is None:
        req = urllib.request.Request(url, method="GET")
        log(f"[http] GET {url}", verbose)
    else:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        log(f"[http] POST {url} (json {len(data)} bytes)", verbose)

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
            log(f"[http] {url} -> HTTP {getattr(resp, 'status', '200')} ({len(body)} chars)", verbose)
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code} calling {url}\n{body}".strip())
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error calling {url}: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON from {url}: {e}")


def pick_model(host: str, explicit_model: Optional[str], verbose: bool) -> str:
    if explicit_model:
        log(f"[ollama] Using explicit model: {explicit_model}", verbose)
        return explicit_model

    env_model = os.environ.get("OLLAMA_MODEL", "").strip()
    if env_model:
        log(f"[ollama] Using model from OLLAMA_MODEL: {env_model}", verbose)
        return env_model

    tags_url = host.rstrip("/") + TAGS_PATH
    data = http_json(tags_url, verbose=verbose)
    models = data.get("models") or []
    if not models:
        raise RuntimeError(
            f"No models found at {tags_url}. "
            "Pull a model on the Ollama server (e.g., `ollama pull llama3.1`) and retry."
        )

    first = models[0]
    name = first.get("name")
    if not name:
        raise RuntimeError(f"Unexpected /api/tags response format: {data}")

    log(f"[ollama] Auto-selected model from /api/tags: {name}", verbose)
    return name


def ollama_generate(host: str, model: str, prompt: str, timeout_s: int = 900, verbose: bool = False) -> str:
    url = host.rstrip("/") + GENERATE_PATH
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    log(f"[ollama] Generating with model={model} prompt_chars={len(prompt)}", verbose)
    data = http_json(url, payload=payload, timeout_s=timeout_s, verbose=verbose)
    resp = data.get("response")
    if resp is None:
        raise RuntimeError(f"Unexpected /api/generate response: {json.dumps(data)[:2000]}")
    return str(resp)


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
    }.get(ext, "")

    return (
        REVIEW_PROMPT
        + f"\n\nFile: {path_rel}\n"
        + trunc_note
        + f"\n```{lang}\n{content}\n```\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Review files touched in last Git commit using Ollama; output Markdown.")
    ap.add_argument("--host", default=DEFAULT_HOST, help=f"Ollama host base URL (default: {DEFAULT_HOST})")
    ap.add_argument("--model", default=None, help="Ollama model name (default: first from /api/tags or $OLLAMA_MODEL)")
    ap.add_argument("--out", default=None, help="Write Markdown report to this file (default: stdout)")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS_PER_FILE, help="Max characters to send per file")
    ap.add_argument(
        "--include-nontext",
        action="store_true",
        help="Attempt to send non-text files too (default: skip binary files)",
    )
    ap.add_argument(
        "--v",
        action="store_true",
        help="Verbose: print progress/actions to stderr",
    )
    args = ap.parse_args()

    verbose = bool(args.v)

    log("[init] Starting review script", verbose)
    ensure_git_repo(verbose)

    root = repo_root(verbose)
    log(f"[init] Repo root: {root}", verbose)
    log(f"[init] Current working directory: {os.getcwd()}", verbose)

    commit_sha, commit_subject, commit_date = last_commit_info(verbose)
    log(f"[git] HEAD: {commit_sha}", verbose)
    log(f"[git] Subject: {commit_subject}", verbose)
    log(f"[git] Date: {commit_date}", verbose)

    files_rel = files_touched_in_last_commit(verbose)
    log(f"[git] Files touched in HEAD: {len(files_rel)}", verbose)
    for f in files_rel:
        log(f"  - {f}", verbose)

    model = pick_model(args.host, args.model, verbose)

    now = _dt.datetime.now().isoformat(timespec="seconds")
    md_parts: List[str] = []
    md_parts.append("# C++/Qt Change Review (Last Commit)\n")
    md_parts.append(f"- Repo: `{root}`\n")
    md_parts.append(f"- Commit: `{commit_sha}`\n")
    md_parts.append(f"- Subject: {commit_subject}\n")
    md_parts.append(f"- Commit date: {commit_date}\n")
    md_parts.append(f"- Generated: {now}\n")
    md_parts.append(f"- Ollama host: `{args.host}`\n")
    md_parts.append(f"- Model: `{model}`\n")
    md_parts.append("\n---\n\n")

    if not files_rel:
        md_parts.append("No files found in the last commit.\n")
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

        abs_path = os.path.join(root, path_rel)
        log(f"[file] #{i} relative={path_rel}", verbose)
        log(f"[file] #{i} absolute={abs_path}", verbose)

        if not os.path.exists(abs_path):
            md_parts.append(
                textwrap.dedent(
                    f"""\
                    **Skipped:** file not present in working tree.

                    Git reported the path relative to the repo root:

                    - Relative: `{path_rel}`
                    - Absolute checked: `{abs_path}`

                    Common causes:
                    - You ran the script from a subdirectory and previously used relative checks (fixed now).
                    - The file was deleted/renamed after the commit.
                    - You're running in a different worktree/checkout than the commit you expect.

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
            log(
                f"[file] #{i} read ok chars={len(content)} truncated={truncated} max_chars={args.max_chars}",
                verbose,
            )
        except OSError as e:
            md_parts.append(f"**Error reading file:** `{e}`\n\n---\n\n")
            log(f"[file] #{i} ERROR reading: {e}", verbose)
            continue

        prompt = build_file_prompt(path_rel, content, truncated)
        log(f"[ollama] #{i} calling /api/generate ...", verbose)

        try:
            resp = ollama_generate(args.host, model, prompt, verbose=verbose)
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
