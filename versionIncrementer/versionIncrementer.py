"""
Version bump utility for Qt/QMake-style project files.

What it does
------------
1) Starts from the current working directory and discovers the Git repository root.
2) Reads a semantic version (MAJOR.MINOR.PATCH) from a *source* branch (default: "development")
   WITHOUT checking out or switching branches.
3) Computes the next version by bumping PATCH (+1).
4) Updates the VERSION assignment line in the working tree file.

Defaults
--------
- File: MPT.pro (relative to repo root)
- Source branch: development

Usage
-----
    python versionIncrementer.py
    python versionIncrementer.py -v
    python versionIncrementer.py --file subdir/MPT.pro
    python versionIncrementer.py --source-branch main -v
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final


LOG = logging.getLogger("version_bump")


@dataclass(frozen=True, slots=True)
class SemVer:
    """
    Immutable semantic version (MAJOR.MINOR.PATCH).

    :param major: Major version component.
    :param minor: Minor version component.
    :param patch: Patch version component.
    """

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> "SemVer":
        """
        Parse a semantic version string into a :class:`~SemVer`.

        Accepts strings of the form ``MAJOR.MINOR.PATCH`` (optionally surrounded by whitespace).

        :param text: Version text to parse.
        :returns: Parsed semantic version.
        :rtype: SemVer
        :raises ValueError: If *text* does not match ``MAJOR.MINOR.PATCH``.
        """
        m = re.fullmatch(r"\s*(\d+)\.(\d+)\.(\d+)\s*", text)
        if not m:
            raise ValueError(f"Invalid semantic version: {text!r}")
        return cls(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    def bump_patch(self) -> "SemVer":
        """
        Return a new version with ``patch`` incremented by 1.

        :returns: New semantic version with ``patch + 1``.
        :rtype: SemVer
        """
        return SemVer(self.major, self.minor, self.patch + 1)

    def __str__(self) -> str:
        """
        Render the version as ``MAJOR.MINOR.PATCH``.

        :returns: String representation of the semantic version.
        :rtype: str
        """
        return f"{self.major}.{self.minor}.{self.patch}"


class GitError(RuntimeError):
    """
    Raised when a Git command fails or cannot be executed.
    """
    pass

def run_git(args: list[str], *, cwd: Path) -> str:
    """
    Execute a Git command and return its stdout.

    The command is executed as ``git <args...>`` with the given working directory. On failure,
    a :class:`~GitError` is raised with a concise diagnostic that includes exit status and
    command output (where available).

    :param args: Git command arguments (excluding the leading ``git``).
    :param cwd: Directory in which to run the Git command.
    :returns: Stdout of the Git command, stripped of leading/trailing whitespace.
    :rtype: str
    :raises GitError: If Git is not available, cannot be executed, or returns a non-zero exit code.
    """
    cmd = ["git", *args]
    LOG.debug("Running: %s", " ".join(cmd))

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise GitError("git executable not found (is Git installed and on PATH?)") from exc
    except subprocess.CalledProcessError as exc:
        stdout = (exc.stdout or "").strip()
        stderr = (exc.stderr or "").strip()
        details = "; ".join(part for part in [stderr, stdout] if part) or "no output"
        raise GitError(f"git {' '.join(args)} failed (exit {exc.returncode}): {details}") from exc
    except OSError as exc:
        raise GitError(f"failed to run git {' '.join(args)}: {exc}") from exc

    return proc.stdout.strip()


def get_repo_root(start_dir: Path) -> Path:
    """
    Determine the root directory of the Git repository containing *start_dir*.

    Internally calls ``git rev-parse --show-toplevel``.

    :param start_dir: Starting directory within (or below) a Git repository.
    :returns: Absolute path of the repository root.
    :rtype: pathlib.Path
    :raises GitError: If *start_dir* is not within a Git repository or Git cannot be executed.
    """
    root = run_git(["rev-parse", "--show-toplevel"], cwd=start_dir)
    return Path(root)


def resolve_target_path(repo_root: Path, user_path: str) -> Path:
    """
    Resolve the user-provided file path into an absolute path.

    - Expands ``~`` in *user_path*.
    - If *user_path* is relative, it is resolved relative to *repo_root*.
    - The resulting path is fully resolved (symlinks/``..`` removed).

    :param repo_root: Repository root used as the base for relative paths.
    :param user_path: Path provided by the user (absolute or relative).
    :returns: Absolute resolved path for the target file.
    :rtype: pathlib.Path
    """
    expanded = Path(os.path.expanduser(user_path))
    if expanded.is_absolute():
        return expanded.resolve()
    return (repo_root / expanded).resolve()


def ensure_within_repo(repo_root: Path, target_path: Path) -> None:
    """
    Validate that *target_path* is located within *repo_root*.

    This prevents accidental or malicious modification of files outside the repository.

    :param repo_root: Repository root directory.
    :param target_path: Candidate path to validate.
    :raises ValueError: If *target_path* is not under *repo_root*.
    """
    repo_root = repo_root.resolve()
    target_path = target_path.resolve()
    try:
        target_path.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"Refusing to modify file outside repository: {target_path}") from exc


def ensure_tracked_file(repo_root: Path, target_path: Path) -> None:
    """
    Validate that *target_path* is tracked by Git in the current working tree.

    This prevents modifying arbitrary/untracked files that happen to live under the repository directory.

    :param repo_root: Repository root directory.
    :param target_path: Absolute path to validate.
    :raises GitError: If the file is not tracked by Git.
    """
    rel = target_path.relative_to(repo_root).as_posix()
    run_git(["ls-files", "--error-unmatch", "--", rel], cwd=repo_root)


def ensure_exists_in_branch(repo_root: Path, branch: str, target_path: Path) -> None:
    """
    Validate that *target_path* exists on *branch*.

    This prevents bumping based on missing or renamed files in the source branch.

    :param repo_root: Repository root directory.
    :param branch: Branch (or any Git tree-ish) to verify against.
    :param target_path: Absolute path of the file.
    :raises GitError: If the file does not exist on the specified branch.
    """
    rel = target_path.relative_to(repo_root).as_posix()
    run_git(["cat-file", "-e", f"{branch}:{rel}"], cwd=repo_root)


def read_file_from_branch(repo_root: Path, branch: str, file_path: Path) -> str:
    """
    Read the content of *file_path* from *branch* without checking out the branch.

    Internally calls ``git show <branch>:<path>``.

    :param repo_root: Repository root directory.
    :param branch: Branch (or any Git tree-ish) to read from.
    :param file_path: Absolute path of the file in the working tree.
    :returns: File contents from the specified branch.
    :rtype: str
    :raises GitError: If the branch, path, or repository state prevents reading via Git.
    """
    rel = file_path.relative_to(repo_root)
    spec = f"{branch}:{rel.as_posix()}"
    return run_git(["show", spec], cwd=repo_root)


VERSION_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<prefix>\s*VERSION\s*=\s*)(?P<version>\d+\.\d+\.\d+)(?P<suffix>\s*(?:#.*)?)$"
)


def extract_version(content: str) -> SemVer:
    """
    Extract exactly one ``VERSION = MAJOR.MINOR.PATCH`` assignment from file content.

    :param content: File content to scan.
    :returns: Extracted semantic version.
    :rtype: SemVer
    :raises ValueError: If no VERSION line is found or multiple VERSION lines are found.
    """
    matches: list[str] = []
    for line in content.splitlines():
        m = VERSION_LINE_RE.match(line)
        if m:
            matches.append(m.group("version"))

    if not matches:
        raise ValueError("No VERSION = X.Y.Z line found.")
    if len(matches) > 1:
        raise ValueError("Multiple VERSION lines found.")

    return SemVer.parse(matches[0])


def update_version(content: str, new_version: SemVer) -> str:
    """
    Replace exactly one ``VERSION = MAJOR.MINOR.PATCH`` assignment in *content*.

    Preserves:
    - Leading whitespace and formatting around ``VERSION =`` (via regex capture).
    - Any trailing comment (``# ...``) on the VERSION line.
    - The original line ending style (LF vs CRLF) for the modified line.

    :param content: Original file content.
    :param new_version: Version to write into the VERSION assignment.
    :returns: Updated file content with the VERSION line modified.
    :rtype: str
    :raises ValueError: If no VERSION line is found or multiple VERSION lines are found.
    """
    lines = content.splitlines(keepends=True)
    hits: list[tuple[int, re.Match[str]]] = []

    for i, line in enumerate(lines):
        m = VERSION_LINE_RE.match(line.rstrip("\r\n"))
        if m:
            hits.append((i, m))

    if not hits:
        raise ValueError("No VERSION = X.Y.Z line found.")
    if len(hits) > 1:
        raise ValueError("Multiple VERSION lines found.")

    idx, m = hits[0]
    newline = "\r\n" if lines[idx].endswith("\r\n") else "\n"
    lines[idx] = f"{m.group('prefix')}{new_version}{m.group('suffix')}{newline}"
    return "".join(lines)


def atomic_write_text(path: Path, content: str, *, encoding: str) -> None:
    """
    Atomically write *content* to *path*.

    Writes to a temporary file in the same directory and then replaces the target using
    :func:`os.replace`, which is atomic on Windows and Linux when source and target are on
    the same filesystem.

    :param path: Target file path.
    :param content: Text content to write.
    :param encoding: Text encoding used for writing.
    :raises OSError: If writing or replacing fails.
    """
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(content, encoding=encoding)
    os.replace(tmp, path)


def configure_logging(verbose: bool) -> None:
    """
    Configure root logging for console output.

    :param verbose: If ``True``, set log level to ``DEBUG``; otherwise ``INFO``.
    :returns: None
    :rtype: None
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    :returns: Parsed arguments namespace with attributes:
              ``file`` (str), ``source_branch`` (str), ``verbose`` (bool).
    :rtype: argparse.Namespace
    """
    p = argparse.ArgumentParser(description="Increment patch version from another branch without checkout.")
    p.add_argument(
        "--file",
        default="MPT.pro",
        help="Target file path (default: MPT.pro relative to repo root)",
    )
    p.add_argument(
        "--source-branch",
        default="development",
        help="Branch to read VERSION from (default: %(default)s)",
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return p.parse_args()


def main() -> int:
    """
    Program entry point.

    - Discovers the repository root.
    - Resolves and validates the target file path.
    - Enforces that the file is tracked and exists on the source branch.
    - Reads VERSION from the source branch, bumps patch, and writes it into the working tree file
      using an atomic replace.

    :returns: Process exit code (0 on success; 2 on failure).
    :rtype: int
    """
    args = parse_args()
    configure_logging(args.verbose)

    try:
        start_dir = Path.cwd()
        repo_root = get_repo_root(start_dir)
        LOG.debug("Repo root: %s", repo_root)

        target_path = resolve_target_path(repo_root, args.file)
        ensure_within_repo(repo_root, target_path)
        ensure_tracked_file(repo_root, target_path)
        ensure_exists_in_branch(repo_root, args.source_branch, target_path)
        LOG.debug("Target file: %s", target_path)

        if not target_path.is_file():
            raise FileNotFoundError(f"Target file not found: {target_path}")

        source_content = read_file_from_branch(repo_root, args.source_branch, target_path)
        old_version = extract_version(source_content)
        new_version = old_version.bump_patch()

        encoding = "utf-8"
        working_content = target_path.read_text(encoding=encoding)
        updated = update_version(working_content, new_version)
        atomic_write_text(target_path, updated, encoding=encoding)

        LOG.info("VERSION updated: %s -> %s (from %s)", old_version, new_version, args.source_branch)
        return 0

    except Exception as exc:
        if getattr(args, "verbose", False):
            LOG.exception("Unhandled error")
        else:
            LOG.error("%s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
