# Boldemort

Convert inline Markdown styling to Unicode-styled characters — no dependencies, pure Python 3.

Works wherever you paste text: LinkedIn posts, Slack messages, GitHub comments, Twitter/X, anywhere that renders Unicode but ignores Markdown.

---

## What it does

| Markdown input    | Unicode output | Style          |
|-------------------|----------------|----------------|
| `**bold text**`   | 𝗯𝗼𝗹𝗱 𝘁𝗲𝘅𝘁      | Sans-serif bold |
| `__bold text__`   | 𝗯𝗼𝗹𝗱 𝘁𝗲𝘅𝘁      | Sans-serif bold |
| `*italic text*`   | 𝘪𝘵𝘢𝘭𝘪𝘤 𝘵𝘦𝘹𝘵    | Sans-serif italic |
| `_italic text_`   | 𝘪𝘵𝘢𝘭𝘪𝘤 𝘵𝘦𝘹𝘵    | Sans-serif italic |
| `` `mono text` `` | 𝚖𝚘𝚗𝚘 𝚝𝚎𝚡𝚝      | Monospace |
| `~~strike~~`      | s̶t̶r̶i̶k̶e̶         | Combining strikethrough |

All other text is passed through unchanged. Block-level Markdown (headings, lists, tables) is intentionally not touched.

---

## Requirements

- Python 3.9+
- Zero runtime dependencies

---

## Usage

### Read from stdin, write to stdout

```bash
echo '**Hello**, *world*!' | python3 boldemort.py
# → 𝗛𝗲𝗹𝗹𝗼, 𝘸𝘰𝘳𝘭𝘥!
```

### Read from a file

```bash
python3 boldemort.py input.md
```

### Write output to a file

```bash
python3 boldemort.py input.md -o output.txt
```

### Pipe into clipboard (macOS / Linux)

```bash
# macOS
echo '**important**' | python3 boldemort.py | pbcopy

# Linux (xclip)
echo '**important**' | python3 boldemort.py | xclip -selection clipboard
```

---

## Install as a command

Copy the script somewhere on your `PATH`:

```bash
cp boldemort.py ~/.local/bin/boldemort
chmod +x ~/.local/bin/boldemort

echo '**done**' | boldemort
```

---

## End-to-end test case

A complete sample document covering every supported style lives in
`testmaterial/test_input.md`. Run the converter against it and inspect the
rendered output:

```bash
python3 boldemort.py testmaterial/test_input.md -o testmaterial/test_output.txt
cat testmaterial/test_output.txt
```

Or stream directly to your terminal:

```bash
python3 boldemort.py testmaterial/test_input.md
```

### What the test file covers

| Section | Markdown used | Expected transformation |
|---------|--------------|------------------------|
| Bold | `**double asterisks**`, `__double underscores__` | Sans-serif bold letters/digits |
| Italic | `*single asterisks*`, `_single underscores_` | Sans-serif italic letters |
| Monospace | `` `backticks` `` | Monospace letters/digits; punctuation passes through |
| Strikethrough | `~~double tildes~~` | U+0336 overlay after every character |
| Mixed | All four styles on one line | Each span converted independently |
| Passthrough | Plain text, `$100`, `x*y`, dangling markers | Identical to input — nothing altered |

### Verify the output manually

Check these key lines in `testmaterial/test_output.txt`:

```
Use 𝗱𝗼𝘂𝗯𝗹𝗲 𝗮𝘀𝘁𝗲𝗿𝗶𝘀𝗸𝘀 to make text bold.
Use 𝘴𝘪𝘯𝘨𝘭𝘦 𝘢𝘴𝘵𝘦𝘳𝘪𝘴𝘬𝘴 to italicize.
Inline code uses 𝚋𝚊𝚌𝚔𝚝𝚒𝚌𝚔𝚜.
Use d̶o̶u̶b̶l̶e̶ ̶t̶i̶l̶d̶e̶s̶ to strike through text.
𝗕𝗼𝗹𝗱, 𝘪𝘵𝘢𝘭𝘪𝘤, 𝚖𝚘𝚗𝚘, and s̶t̶r̶u̶c̶k̶ all on one line.
Prices like $100 and formulas like x*y are not touched.
A single *dangling asterisk with no close stays raw.
```

---

## Development

### Run linters

```bash
python3 -m mypy --strict boldemort.py
python3 -m flake8 boldemort.py tests/ --max-line-length=88
```

### Run tests

```bash
python3 -m pytest tests/ -v
```

All 44 tests must pass before committing. See `agents.md` for the full contributor conventions.

---

## Unicode blocks used

| Style | Unicode block | Range |
|-------|--------------|-------|
| Sans-serif bold | Mathematical Alphanumeric Symbols | U+1D5D4–U+1D607, U+1D7EC–U+1D7F5 |
| Sans-serif italic | Mathematical Alphanumeric Symbols | U+1D608–U+1D63B |
| Monospace | Mathematical Alphanumeric Symbols | U+1D670–U+1D6A3, U+1D7F6–U+1D7FF |
| Strikethrough | Combining Diacritical Marks | U+0336 |

Strikethrough uses U+0336 COMBINING LONG STROKE OVERLAY inserted after each character, since there is no dedicated strikethrough block in Unicode's math alphanumeric range.

---

## Limitations

- Characters outside A–Z, a–z, 0–9 (accented letters, punctuation, CJK, etc.) are
  passed through as-is within styled spans — only ASCII alphanumerics have
  Mathematical Alphanumeric equivalents.
- Nested spans (e.g. `**_bold-italic_**`) are not supported; the outermost
  pattern wins.
- Patterns must not cross newlines.
