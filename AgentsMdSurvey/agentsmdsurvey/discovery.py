"""Layer 1 — collection.

Walks a directory tree, finds agent instruction files, attributes each to a
project and a git repository, and records provenance. Fully deterministic: no
model, no network, read-only against the scanned tree.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# Filenames that harnesses actually read, mapped to the harness family.
# Matching is case-insensitive because the corpus mixes AGENTS.md, agents.md
# and agent.md, and that inconsistency is itself a finding.
FILENAME_KINDS: dict[str, str] = {
    "agents.md": "agents_md",
    "agent.md": "agents_md",
    "agents.local.md": "agents_md",
    "claude.md": "claude_md",
    "claude.local.md": "claude_md",
    "gemini.md": "gemini_md",
    "codex.md": "codex_md",
    ".cursorrules": "cursor",
    ".windsurfrules": "windsurf",
    ".aider.conf.yml": "aider",
    "copilot-instructions.md": "copilot",
    "skill.md": "skill",
    "settings.json": "claude_settings",
    "settings.local.json": "claude_settings",
}

# Only files named settings*.json that live inside a .claude directory count.
_CLAUDE_DIR_ONLY = {"claude_settings"}

# Directories never worth walking into: caches, virtualenvs, package stores.
PRUNE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "site-packages",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".tox",
        ".gradle",
        ".idea",
        ".vscode-test",
        "venv",
        ".venv",
        "env",
        ".env",
        ".cache",
        ".terraform",
        "Pods",
    }
)

# Path components that mark a file as somebody else's instructions rather than
# ours. Build outputs are deliberately NOT listed here: a copy under build/ is
# a duplicate of our own file, which is a different finding.
VENDOR_MARKERS: frozenset[str] = frozenset(
    {
        "node_modules",
        "vendor",
        "third_party",
        "thirdparty",
        "external",
        "externals",
        "subprojects",
        "runtime",
        ".tooling",
        "deps",
        "_deps",
    }
)

# Path components that mark a generated or copied location.
GENERATED_MARKERS: frozenset[str] = frozenset(
    {"build", "dist", "out", "target", "_build", "cmake-build-debug", "cmake-build-release"}
)

# Directories a project uses to park documentation. A file found here belongs
# to the project one level up, not to the docs directory.
DOC_DIRS: frozenset[str] = frozenset(
    {"docs", "doc", "documents", "documentation", ".github", ".claude", ".codex", ".cursor"}
)

# Files whose presence means "a project starts here".
PROJECT_MARKERS: frozenset[str] = frozenset(
    {
        ".git",
        "pyproject.toml",
        "setup.py",
        "package.json",
        "CMakeLists.txt",
        "Cargo.toml",
        "go.mod",
        "pubspec.yaml",
        "build.gradle",
        "build.gradle.kts",
        "Makefile",
        "requirements.txt",
        "platformio.ini",
        "CMakePresets.json",
    }
)


@dataclass
class InstructionFile:
    """One discovered instruction file with everything Layer 1 can know."""

    path: str  # absolute
    rel_path: str  # relative to the scan root
    name: str
    kind: str  # agents_md, claude_md, skill, ...
    project: str  # nearest project-marker ancestor, relative to the scan root
    project_path: str  # absolute
    scope: str  # the directory these instructions actually govern
    repo_root: str | None  # nearest ancestor holding .git
    location: str  # root | docs | dot-dir | nested
    size_bytes: int
    line_count: int
    sha256: str
    text: str = field(repr=False, default="")
    vendored: bool = False
    generated: bool = False
    vendor_reason: str = ""
    # git provenance, empty when the file is untracked or git is unavailable
    last_commit_date: str = ""
    first_commit_date: str = ""
    commit_count: int = 0
    author_emails: list[str] = field(default_factory=list)

    @property
    def group_key(self) -> str:
        """First-party files only ever count once per scope and kind."""
        return f"{self.scope}::{self.kind}"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _classify_kind(name: str, parent_parts: tuple[str, ...]) -> str | None:
    kind = FILENAME_KINDS.get(name.lower())
    if kind is None:
        return None
    if kind in _CLAUDE_DIR_ONLY and ".claude" not in parent_parts:
        return None
    if kind == "copilot" and ".github" not in parent_parts:
        return None
    return kind


def _find_project(path: Path, root: Path) -> Path:
    """Deepest ancestor that looks like the start of a project.

    A file in ``docs/`` or ``.claude/`` belongs to the directory above it, so
    those are skipped on the way up. Nested projects inside a monorepo-style
    checkout (``codingWithGPT/tipkickHelper``) resolve to the inner directory,
    which is what a reader means by "project".
    """
    current = path.parent
    while current != root and root in current.parents or current == root:
        if current.name not in DOC_DIRS:
            for marker in PROJECT_MARKERS:
                if (current / marker).exists():
                    return current
        if current == root:
            break
        current = current.parent
    # No marker anywhere: fall back to the first non-doc directory.
    current = path.parent
    while current != root and (current.name in DOC_DIRS or current.name.startswith(".")):
        current = current.parent
    return current


def _find_scope(path: Path, root: Path) -> Path:
    """The directory these instructions govern.

    An instruction file declares that a scope starts where it sits, so the
    scope is the file's own directory — walked up past documentation folders,
    because ``docs/AGENTS.md`` governs the project, not the docs folder. This
    is deliberately finer-grained than the project: one repository can hold
    several independently instructed areas.
    """
    current = path.parent
    # A skill lives at <scope>/[.claude/]skills/<name>/SKILL.md; the scope is
    # whatever sits above the skills container, not the individual skill.
    containers = {"skills", "agents", "commands", "workflows"}
    parts = current.relative_to(root).parts if current != root else ()
    for index, part in enumerate(parts):
        if part.lower() in containers:
            current = root.joinpath(*parts[:index]) if index else root
            break
    while current != root and (current.name in DOC_DIRS or current.name.startswith(".")):
        current = current.parent
    return current


def _find_repo_root(path: Path, root: Path) -> Path | None:
    current = path.parent
    while True:
        if (current / ".git").exists():
            return current
        if current == root or current.parent == current:
            return None
        current = current.parent


def _location(path: Path, project_path: Path) -> str:
    rel = path.relative_to(project_path)
    if len(rel.parts) == 1:
        return "root"
    first = rel.parts[0]
    if first.startswith("."):
        return "dot-dir"
    if first in DOC_DIRS:
        return "docs"
    return "nested"


def _vendor_reason(path: Path, project_path: Path, root: Path) -> str:
    parts = set(path.relative_to(root).parts)
    hit = parts & VENDOR_MARKERS
    if hit:
        return f"path contains {sorted(hit)[0]}/"
    # A nested .git below another repository is a submodule or a vendored clone.
    outer = _find_repo_root(project_path.parent, root) if project_path != root else None
    if outer is not None and (project_path / ".git").exists():
        return f"nested git checkout inside {outer.name}"
    return ""


def _git(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_history(repo: Path, file_path: Path) -> tuple[str, str, int, list[str]]:
    """(last date, first date, commit count, distinct author emails)."""
    log = _git(repo, "log", "--follow", "--format=%aI%x09%ae", "--", str(file_path))
    if not log:
        return "", "", 0, []
    rows = [line.split("\t") for line in log.splitlines() if "\t" in line]
    if not rows:
        return "", "", 0, []
    dates = [r[0][:10] for r in rows]
    emails: list[str] = []
    for _, email in rows:
        if email not in emails:
            emails.append(email)
    return dates[0], dates[-1], len(rows), emails


@dataclass
class RepoInfo:
    """Activity of a git repository, used to rank the coverage backlog."""

    path: str
    name: str
    last_commit_date: str = ""
    commit_count: int = 0

    @classmethod
    def probe(cls, repo: Path) -> "RepoInfo":
        last = _git(repo, "log", "-1", "--format=%aI")
        count = _git(repo, "rev-list", "--count", "HEAD")
        return cls(
            path=str(repo),
            name=repo.name,
            last_commit_date=last[:10],
            commit_count=int(count) if count.isdigit() else 0,
        )


def discover(root: Path, *, use_git: bool = True) -> tuple[list[InstructionFile], list[RepoInfo]]:
    """Find every instruction file under ``root``.

    Returns the files and the git repositories seen while walking, so callers
    can report on repositories that carry no instructions at all.
    """
    root = root.resolve()
    files: list[InstructionFile] = []
    repos: dict[str, RepoInfo] = {}
    git_cache: dict[str, RepoInfo] = {}

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in PRUNE_DIRS)
        here = Path(dirpath)
        if (here / ".git").exists() and str(here) not in repos:
            repos[str(here)] = RepoInfo.probe(here) if use_git else RepoInfo(str(here), here.name)

        for filename in sorted(filenames):
            kind = _classify_kind(filename, here.parts)
            if kind is None:
                continue
            path = here / filename
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="replace")

            project_path = _find_project(path, root)
            scope_path = _find_scope(path, root)
            repo_root = _find_repo_root(path, root)
            rel_parts = set(path.relative_to(root).parts)
            vendor_reason = _vendor_reason(path, project_path, root)

            item = InstructionFile(
                path=str(path),
                rel_path=str(path.relative_to(root)),
                name=filename,
                kind=kind,
                project=str(project_path.relative_to(root)) if project_path != root else ".",
                project_path=str(project_path),
                scope=str(scope_path.relative_to(root)) if scope_path != root else ".",
                repo_root=str(repo_root) if repo_root else None,
                location=_location(path, project_path),
                size_bytes=len(raw),
                line_count=text.count("\n") + (1 if text and not text.endswith("\n") else 0),
                sha256=_sha256(raw),
                text=text,
                vendored=bool(vendor_reason),
                generated=bool(rel_parts & GENERATED_MARKERS),
                vendor_reason=vendor_reason,
            )

            if use_git and repo_root is not None:
                key = str(repo_root)
                if key not in git_cache:
                    git_cache[key] = repos.get(key) or RepoInfo.probe(repo_root)
                last, first, count, emails = _git_history(repo_root, path)
                item.last_commit_date = last
                item.first_commit_date = first
                item.commit_count = count
                item.author_emails = emails

            files.append(item)

    return files, sorted(repos.values(), key=lambda r: r.name.lower())


def mark_duplicates(files: list[InstructionFile]) -> dict[str, list[InstructionFile]]:
    """Group files by content hash and flag every copy but the canonical one.

    The canonical copy is the one that is neither generated nor vendored, with
    the shortest path — the source that the others were produced from.
    """
    groups: dict[str, list[InstructionFile]] = {}
    for item in files:
        groups.setdefault(item.sha256, []).append(item)

    for group in groups.values():
        if len(group) < 2:
            continue
        ranked = sorted(group, key=lambda f: (f.generated, f.vendored, len(f.rel_path), f.rel_path))
        for copy in ranked[1:]:
            copy.generated = True
            if not copy.vendor_reason:
                copy.vendor_reason = f"byte-identical copy of {ranked[0].rel_path}"
    return {h: g for h, g in groups.items() if len(g) > 1}


def first_party(files: list[InstructionFile]) -> list[InstructionFile]:
    """The files that describe our own house style."""
    return [f for f in files if not f.vendored and not f.generated]
