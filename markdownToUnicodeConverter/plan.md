# Plan: Markdown → Unicode Converter ("Unicodown")

## Goal
A dependency-free Python CLI tool that reads Markdown-flavored inline styling
(`**bold**`, `*italic*`, `` `code` ``, `__bold__`, `_italic_`, `~~strike~~`)
and replaces each styled span with the corresponding Unicode Mathematical
Alphanumeric Symbol characters, leaving all other text unchanged.

---

## Scope

### Supported conversions (initial version)

| Markdown syntax | Unicode style                                  | Example input     | Example output |
|-----------------|------------------------------------------------|-------------------|----------------|
| `**text**`      | Mathematical Bold (A–Z a–z 0–9)               | `**Hello**`       | 𝗛𝗲𝗹𝗹𝗼          |
| `__text__`      | Mathematical Bold (same as above)             | `__Hello__`       | 𝗛𝗲𝗹𝗹𝗼          |
| `*text*`        | Mathematical Italic (A–Z a–z)                 | `*Hello*`         | 𝘏𝘦𝘭𝘭𝘰          |
| `_text_`        | Mathematical Italic (same as above)           | `_Hello_`         | 𝘏𝘦𝘭𝘭𝘰          |
| `` `text` ``    | Mathematical Monospace (A–Z a–z 0–9)          | `` `Hello` ``     | 𝙷𝚎𝚕𝚕𝚘          |
| `~~text~~`      | Combining Strikethrough (U+0336 after each char) | `~~gone~~`    | g̶o̶n̶e̶          |

### Out of scope (v1)
- Block-level Markdown (headings, lists, tables, block-code, etc.) — pass through unchanged
- Nested spans (e.g. `**_bold-italic_**`) — outermost match wins
- HTML entities / raw HTML

---

## Architecture

```
unicodown/
├── unicodown.py          # main entry point (CLI + convert logic)
├── tests/
│   └── test_unicodown.py # pytest test suite
├── plan.md               # this file
└── agents.md             # contributor conventions
```

**Single-file core** (`unicodown.py`):
- `str.maketrans` translation tables (zero runtime deps)
- `convert(text: str) -> str` — applies regexes in precedence order
- `main()` — argparse for `[input]` and `-o/--output`

Regex application order (important to avoid double-substitution):
1. Backtick mono (highest precedence — protect content from further substitution)
2. Double-asterisk bold
3. Double-underscore bold
4. Single-asterisk italic
5. Single-underscore italic
6. Double-tilde strikethrough

---

## Testing strategy

- **Unit tests** via `pytest` (stdlib fallback: `unittest`)
- Each conversion type gets ≥ 3 test cases: basic, mixed-case, digits
- Edge cases: empty spans, spans with spaces, spans crossing no-special-chars
- Regression: ensure non-matching text is passed through unmodified
- CLI integration test via `subprocess` (stdin→stdout, file→file, file→stdout)

---

## Linting / quality

- `flake8` — PEP 8 style
- `mypy --strict` — static types
- `pytest` — all tests must pass

---

## Milestones

1. [x] `plan.md` written
2. [x] `agents.md` written
3. [x] Implement `unicodown.py` (translation tables + regex converter + CLI)
4. [x] Write `tests/test_unicodown.py`
5. [x] Run linters clean (mypy --strict + flake8)
6. [x] Run tests clean (44/44)
7. [x] `git init` + initial commit
