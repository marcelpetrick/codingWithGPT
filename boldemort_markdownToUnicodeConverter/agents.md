# Contributor Conventions

## General

- Never mention AI tools, language models, or automated code generation in
  commits, comments, or documentation.
- Write code as if a human authored every line — clear, idiomatic Python.

## Running tests and linters

Before every commit, run the full check suite:

```bash
# Type checking
mypy --strict boldemort.py

# Style
flake8 boldemort.py tests/

# Tests
pytest tests/ -v
```

All checks must pass cleanly (zero errors, zero warnings) before committing.

## Commit messages

Use **Conventional Commits** format:

```
<type>(<scope>): <short imperative summary>

<body — explain why, not what. list significant decisions or tradeoffs>

<footer — breaking changes, issue refs>
```

### Types

| Type       | When to use                                     |
|------------|-------------------------------------------------|
| `feat`     | New user-visible functionality                  |
| `fix`      | Bug fix                                         |
| `refactor` | Internal restructure, no behavior change        |
| `test`     | Adding or fixing tests only                     |
| `docs`     | Documentation only                              |
| `chore`    | Tooling, CI, dependency bumps                   |
| `style`    | Formatting, whitespace, linting — no logic      |

### Rules

- Subject line: ≤ 72 characters, imperative mood ("add", not "added")
- Body: wrap at 72 characters; explain *why*, not *what*
- No trailing period on the subject line
- Reference issues/PRs in the footer if applicable

### Examples

```
feat(converter): add strikethrough support via combining diacritics

Strikethrough has no dedicated Unicode math block, so U+0336 COMBINING
LONG STROKE OVERLAY is inserted after every character. This preserves
copy-paste readability on terminals that strip combining marks.
```

```
fix(cli): handle stdin correctly when piped from another process

Previously the tool would block waiting for EOF on interactive ttys.
Now it reads sys.stdin.buffer in binary mode and decodes as UTF-8 so
the pipe case works without pressing Ctrl-D manually.
```

## Code style

- Standard library only — no third-party runtime dependencies.
- `pytest` is the only allowed test dependency.
- `mypy --strict` must pass with no `# type: ignore` suppressions unless
  unavoidable, in which case add an inline comment explaining why.
- Maximum line length: 88 characters (Black-compatible).
- No commented-out code in committed files.
