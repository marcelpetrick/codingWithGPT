total 52K
drwxr-xr-x   2 mpetrick mpetrick 4.0K Mar  2 17:43 .
drwxrwxrwx 104 mpetrick mpetrick 4.0K Mar  2 17:40 ..
-rw-r--r--   1 mpetrick mpetrick 6.5K Mar  2 17:40 1st_review.md
-rw-r--r--   1 mpetrick mpetrick 1.7K Mar  2 17:40 2nd_review.md
-rw-r--r--   1 mpetrick mpetrick 1.1K Mar  2 17:40 functional_requirements.md
-rw-r--r--   1 mpetrick mpetrick  679 Mar  2 17:40 list_models.py
-rw-r--r--   1 mpetrick mpetrick    0 Mar  2 17:43 llm_compat_output.md
-rw-r--r--   1 mpetrick mpetrick  22K Mar  2 17:40 main.py
-------------------- ./main.py --------------------
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
    """
    Always tries to list all available Ollama models to stdout.
    Selection priority:
      1) explicit_model (arg --model)
      2) $OLLAMA_MODEL
      3) any model containing 'coder' (case-insensitive); if multiple, random choice
      4) fallback to first model from /api/tags
    """
    tags_url = host.rstrip("/") + TAGS_PATH

    # Determine preferred override (but still try to list models first)
    override = None
    if explicit_model:
        override = explicit_model.strip()
        log(f"[ollama] Using explicit model override: {override}", verbose)
    else:
        env_model = os.environ.get("OLLAMA_MODEL", "").strip()
        if env_model:
            override = env_model
            log(f"[ollama] Using model override from OLLAMA_MODEL: {override}", verbose)

    models_data = None
    names: List[str] = []

    # Always try to fetch and print available models (best-effort if override is set)
    try:
        models_data = http_json(tags_url, payload=None, cfg=http_cfg, verbose=verbose)
        models = models_data.get("models") or []
        names = [m.get("name") for m in models if isinstance(m, dict) and m.get("name")]

        # Print to STDOUT as requested
        sys.stdout.write("Available Ollama models (/api/tags):\n")
        if names:
            for i, n in enumerate(names, start=1):
                sys.stdout.write(f"  {i:2d}. {n}\n")
        else:
            sys.stdout.write("  (none returned)\n")
        sys.stdout.flush()

    except Exception as e:
        # If user specified a model, don't hard-fail just because listing failed.
        # Otherwise, we do need tags to pick something.
        if override:
            sys.stdout.write(
                "Available Ollama models (/api/tags):\n"
                f"  (failed to query {tags_url}: {e})\n"
            )
            sys.stdout.flush()
            return override
        raise

    # If we have an override and tags were reachable, keep using the override.
    if override:
        return override

    if not names:
        raise RuntimeError(
            f"No models found at {tags_url}. Pull a model on the Ollama server and retry."
        )

    coder_matches = [n for n in names if "coder" in n.lower()]
    if coder_matches:
        chosen = random.choice(coder_matches) if len(coder_matches) > 1 else coder_matches[0]
        log(f"[ollama] Auto-selected 'coder' model: {chosen}", verbose)
        return chosen

    chosen = names[0]
    log(f"[ollama] No 'coder' model found; falling back to first model: {chosen}", verbose)
    return chosen


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
---------- end ----------
-------------------- ./2nd_review.md --------------------
python3 main.py --v --directory=.                                                                            ✔ 
[git] Found git at: /usr/bin/git
[git] git version 2.52.0
[init] Start directory: /home/mpetrick/repos/codingWithGPT/ownCodeReview
[git] git -C /home/mpetrick/repos/codingWithGPT/ownCodeReview rev-parse --show-toplevel
[init] Repo root: /home/mpetrick/repos/codingWithGPT
[init] Directory filter (repo-relative): 'ownCodeReview'
[git] git -C /home/mpetrick/repos/codingWithGPT rev-parse HEAD
[git] git -C /home/mpetrick/repos/codingWithGPT log -1 --pretty=%s
[git] git -C /home/mpetrick/repos/codingWithGPT log -1 --pretty=%cI
[git] git -C /home/mpetrick/repos/codingWithGPT show --name-only --pretty= HEAD
[git] HEAD: fda7c84736f43da7fed182cf907d3a56cbd9186c
[git] Files touched in HEAD (all): 1
[git] Files after --directory filter: 1
[http] GET http://192.168.100.32:11434/api/tags
[http] http://192.168.100.32:11434/api/tags -> HTTP 200 (3440 chars)
Available Ollama models (/api/tags):
   1. qwen3:8b
   2. qwen3:4b
   3. freehuntx/qwen3-coder:14b
   4. qwen3-vl:4b
   5. qwen3-vl:8b
   6. qwen2.5vl:7b
   7. qwen3-embedding:4b
   8. qwen3:14b
   9. DC1LEX/nomic-embed-text-v1.5-multimodal:latest
  10. nomic-embed-text-v1.5-multimodal:latest
[ollama] Auto-selected 'coder' model: freehuntx/qwen3-coder:14b
[file] #1 relative=ownCodeReview/main.py
[file] #1 resolved=/home/mpetrick/repos/codingWithGPT/ownCodeReview/main.py
[file] #1 read chars=22287 truncated=False
[ollama] #1 /api/generate ...
[ollama] Generating model=freehuntx/qwen3-coder:14b prompt_chars=22734
[http] POST http://192.168.100.32:11434/api/generate (json 24074 bytes)

---------- end ----------
-------------------- ./list_models.py --------------------
import json
import sys
import urllib.request

HOST = "http://192.168.100.32:11434"
# HOST = "http://localhost:11434"   # change if needed
TAGS_PATH = "/api/tags"

def main():
    url = HOST.rstrip("/") + TAGS_PATH
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.load(resp)
    except Exception as e:
        print(f"Error connecting to Ollama at {url}: {e}", file=sys.stderr)
        sys.exit(1)

    models = data.get("models", [])
    if not models:
        print("No models found.")
        return

    for m in models:
        name = m.get("name")
        if name:
            print(name)

if __name__ == "__main__":
    main()
---------- end ----------
-------------------- ./1st_review.md --------------------
`

**Critical Analysis of Ollama Endpoint:**
1. The specified endpoint `http://192.168.100.32:11434/api/tags` is for listing model tags, not for code analysis
2. The script uses `api/generate` which is the correct endpoint for model inference
3. The model name should be specified (e.g., "codellama" or "qwen2")
4. The script assumes the Ollama instance is running and accessible

**Implementation Notes:**
1. The script uses Git to get changed files from the last commit
2. It sends each file to the Ollama API with the specified prompt
3. The results are formatted into a markdown file
4. It handles basic error cases

**To use:**
1. Ensure Ollama is running with the appropriate model
2. Make sure the script has execute permissions
3. Run in the root of your Git repository

**Potential Improvements:**
1. Add authentication if required
2. Implement rate limiting
3. Add support for different models
4. Implement more detailed error handling
5. Add support for streaming responses

This script provides a basic framework that you can expand based on your specific requirements and Ollama setup.

---

## 2. ownCodeReview/main.py
The Python script provided is a tool for reviewing code changes in a Git repository using an Ollama model. While the script is functional for its intended purpose, there are several areas that could be improved for robustness, safety, and compatibility, especially in embedded or cross-compilation environments. Below is a detailed review of critical issues and recommendations:

---

### **1. File Handling and Security**
- **Issue**: The script reads files directly from the filesystem without proper validation or sanitization of paths. This could lead to unintended file access if the script is run with elevated privileges.
- **Recommendation**: 
  - Validate and sanitize file paths to ensure they are within the expected working directory.
  - Avoid using `os.path.join` without checking for path traversal vulnerabilities (e.g., `../`).

---

### **2. Git Interaction**
- **Issue**: The script relies on Git commands to determine files in the last commit. If Git is not installed or misconfigured, the script will fail silently or raise errors.
- **Recommendation**:
  - Add explicit checks for Git availability (e.g., `which git` or `git --version`).
  - Handle Git errors gracefully (e.g., `subprocess.CalledProcessError` for non-zero exit codes).

---

### **3. Ollama Communication**
- **Issue**: The script assumes the Ollama server is running and accessible. If the server is unreachable or the model is invalid, the script will raise unhandled exceptions.
- **Recommendation**:
  - Implement retries with exponential backoff for network failures.
  - Add timeout parameters for Ollama requests to prevent hanging.
  - Log detailed error messages for Ollama-related failures.

---

### **4. Unicode and Encoding**
- **Issue**: The script writes Markdown reports using UTF-8 encoding, which is standard, but may fail in environments with non-UTF-8 locale settings.
- **Recommendation**:
  - Set the locale explicitly (e.g., `locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')`) if the environment is known to have specific settings.
  - Ensure all output is encoded in UTF-8 to avoid encoding errors.

---

### **5. Resource Management**
- **Issue**: The script processes large files by truncating content, which could be memory-intensive for very large files.
- **Recommendation**:
  - Use streaming or chunked reading for large files to avoid excessive memory usage.
  - Add a warning or log message when truncation occurs to inform users.

---

### **6. Error Handling and Logging**
- **Issue**: The script uses `print` for logging, which is not ideal for structured logging or debugging in production environments.
- **Recommendation**:
  - Replace `print` with Python's `logging` module for better control over log levels, output formatting, and file rotation.
  - Include detailed error messages for unhandled exceptions.

---

### **7. Cross-Compilation and Deployment**
- **Issue**: The script is written in Python, which is platform-independent, but deployment on embedded systems may require Python to be available and properly configured.
- **Recommendation**:
  - Ensure the target environment has Python installed and compatible with the script's dependencies.
  - Consider packaging the script with a virtual environment or container for consistent deployment.

---

### **8. Missing Edge Case Handling**
- **Issue**: The script skips non-text files by default, but binary files may contain critical metadata (e.g., `.pro`, `.pri` files in Qt projects).
- **Recommendation**:
  - Allow users to specify whether to include non-text files via a flag.
  - Add a heuristic to detect and process specific binary files (e.g., `.qrc`, `.ui`) if necessary.

---

### **9. Performance Considerations**
- **Issue**: Processing many files in a large repository may be slow due to repeated file reads and Ollama calls.
- **Recommendation**:
  - Batch file processing or parallelize Ollama calls if feasible.
  - Add a progress indicator or status updates to improve user experience.

---

### **10. Code Structure and Readability**
- **Issue**: The script is dense with logic and error handling, making it harder to maintain or extend.
- **Recommendation**:
  - Break the script into smaller functions (e.g., `fetch_files_from_git`, `process_file`, `generate_report`).
  - Add docstrings and comments for clarity, especially for complex logic.

---

### **Summary of Critical Issues**
| Issue | Severity | Recommendation |
|------|---------|----------------|
| Missing Git availability checks | Medium | Add explicit Git checks |
| Unhandled Ollama errors | High | Implement retries and timeouts |
| File path sanitization | Medium | Validate and sanitize paths |
| Unicode locale assumptions | Low | Set explicit locale settings |
| Lack of structured logging | Medium | Use `logging` module |
| Resource-intensive file handling | Medium | Use streaming for large files |

---

### **Conclusion**
The script is functional but lacks robustness in error handling, security, and cross-platform compatibility. Improvements in these areas will make it more reliable for use in embedded or production environments. While the script itself is not written in C++/Qt (as per the user's initial request), the review highlights best practices for ensuring safety and reliability in similar tools. If the user intended to review C++/Qt code, they should provide that code for a more targeted analysis.

---

[out] Wrote report to stdout
[done] Completed
---------- end ----------
-------------------- ./functional_requirements.md --------------------
write me a python3 script, wich uses this ollama enpoint to review changed files from a cpp project.

the ollama insance you shall use: http://192.168.100.32:11434/api/tags

run it for each touched file sequentially. files for input are those from the last local commit. use the git history of the current working directory / repo then.

output as markdown.

the prompt aplplied toshall be file each file:

------
Act as an expert reviewer for GCC-built C++/Qt (QML) on embedded + desktop Linux. I will paste C++/QML/CMake/qmake. Find critical failures: runtime crashes/UB, deadlocks, QObject ownership bugs, QML binding loops/null access, plugin/module loading failures, and cross-compilation/deployment breakages.

Return:

Top 10 critical issues (ranked) with exact fixes.

Cross-compile + deployment red flags: sysroot/toolchain, host contamination, pkg-config, install layout, RPATH, Qt plugins/QML imports/qt.conf.

One-hour patch list: smallest changes to reduce crash risk and deployment failures fastest.

Be direct; include corrected snippets.
------
---------- end ----------
