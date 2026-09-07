# pythonInterpreterCodeGolf

A Python interpreter written in C, then golfed down step by step.
Not a *complete* Python - a subset large enough to run real programs like the
FizzBuzz in [`program.py`](program.py), fed to the interpreter on stdin:

```sh
make && ./bin/pygolf < program.py     # 101 lines, byte-identical to CPython
```

The challenge came from a screenshot of someone's `python1024.c`
([`input_python1024running.png`](input_python1024running.png)): 1024 bytes of C
that runs FizzBuzz written in Python. Nothing here is copied from it or from
anywhere else - the design below was worked out from scratch, and the golfing
was done one measurable step at a time.

**Result: 1021 bytes for the full subset, 644 bytes for a FizzBuzz-only build.**

## Results

Every version is checked by `./run_tests.sh`, which diffs its output against
real CPython for each test program. v1-v9 run the whole subset (6 programs);
v10 and v11 are deliberately reduced to what FizzBuzz needs (1 program).

| Version | Bytes | Saved | Tests | What changed | What it cost |
|---|---:|---:|:--:|---|---|
| v1  | 9900 |     - | 6/6 | Readable reference: name table, error messages, comments | - |
| v2  | 2511 | -7389 | 6/6 | Mechanical shrink: no comments, one-letter names, `int` | readability |
| v3  | 2146 |  -365 | 6/6 | Loader normalizes the source; one precedence-climbing evaluator | - |
| v4  | 1636 |  -510 | 6/6 | Names keyed by first letter; keywords by one byte; no `#include` | names must differ in their first letter |
| v5  | 1509 |  -127 | 6/6 | Unary minus for free; merged symbol table; `printf`/`puts` | `'` strings, `\n` escapes |
| v6  | 1352 |  -157 | 6/6 | Unbounded block scan; folded loader state | - |
| v7  | 1244 |  -108 | 6/6 | Operator table drives precedence *and* operation; `switch`; macros | - |
| v8  | 1125 |  -119 | 6/6 | Global cursor instead of `char**`; `strtol`; K&R implicit `int` | - |
| v9  | **1021** |  -104 | 6/6 | Strings NUL-terminated at load; shared statement advance; layout | see limitations |
| v10 |  671 |  -350 | 1/1 | FizzBuzz-only: drops `while`, `range` steps, comments, parens, `<`/`>` | subset shrinks |
| v11 |  **644** |   -27 | 1/1 | Final byte squeeze, one line | - |

v9 is the last version that still runs the whole subset, and it is the one that
crosses the 1024-byte line: 9900 bytes down to 1021, a factor of 9.7, with the
same six programs still matching CPython byte for byte. v10 and v11 give up
features on purpose to answer the second question - how small can a C program
be and still run `program.py` - and land at 644.

## How it works, in four stages

### 1. Load

The whole program is read into one buffer with a single `read(0, ...)`.
No file handling, no line buffering.

### 2. Normalize into a line table

One pass rewrites the buffer in place and builds two arrays:

```
T[i] -> the text of line i, with every space outside a string removed
D[i] -> how many spaces that line was indented by
```

Blank lines and comments never enter the table, so an empty line can't cut a
block in half. Deleting the spaces is the single most valuable trick in the
whole program: after it, *nothing below ever has to skip whitespace*, and
keyword offsets become constants. `program.py` turns into:

```
D[]  T[]
 0   defbuzz():
 4   forninrange(101):
 8   ifn%15==0:
12   print("FizzBuzz")
 8   else:
12   ifn%3==0:
...
 0   buzz()
```

So `print(` is always `T[i]+6`, the condition of an `if` always starts at
`T[i]+2`, and a statement is recognised by its *first byte*: `d`, `i`, `w`,
`f`, `p`, `e`.

### 3. Execute a range of lines

There is no syntax tree. The line table **is** the tree, addressed by index
ranges: `X(lo, hi)` runs lines `lo..hi`, and a compound statement owns the
following lines indented deeper than itself:

```c
B(i)  /* first line after i's body */ { j=i; while(D[++j] > D[i]); return j; }
```

`if` runs `X(i+1, e)`; a `for` runs the same range once per iteration; `def`
just records its line number in the symbol table and skips its body; a call
looks that line up and runs its body. Recursion in the interpreter *is*
recursion in the interpreted program. Nothing is compiled ahead of time - a
loop body is re-scanned on every pass, which is slow and wonderfully small.

### 4. Evaluate expressions

One precedence-climbing loop over a global character cursor. An operator's
index in the string `"=!<>+-*/%"` gives both its precedence
(`1+(i>3)+(i>5)`) and which operation to apply:

```c
while (*p && (o = strchr(O,*p)) && (i = o-O, l = 1+(i>3)+(i>5)) > k) {
    p++; p += q = *p=='=' || *p=='/';   /* the second byte of ==, !=, <=, //  */
    x = E(l);                           /* right side, higher precedence only */
    v = ... i-th operation on v and x ...
}
```

Because the recursive call passes `l` and the loop continues only while
precedence is *strictly* greater, operators stay left-associative.

## Golf tricks worth naming

- **Unary minus costs nothing.** The atom parser has no `-` case. Meeting one it
  consumes nothing and returns the variable slot `A['-']`, which no identifier
  can name and which is therefore always 0 - so the main loop reads the `-` as
  a *binary* operator and computes `0-x` by itself. (v8 onwards uses `strtol`,
  which swallows the sign directly and gets `2*-3` right as well.)
- **`<=` is `<` with a bump.** After an operator, one flag `q` says whether a
  second byte was skipped; then `v <= x` is `v < x+1` and `v >= x` is
  `v > x-1`, so four comparisons cost the code of two.
- **The closing quote is the terminator.** The loader writes a `\0` over every
  `"`. A `print` line then starts with `\0` exactly when its argument is a
  string, so `*p ? printf("%d\n", E()) : puts(p+1)` handles both cases.
- **Zeroed globals do the bookkeeping.** The indent array is 0 past the last
  line, so the block scan stops there without any bound check.
- **gnu89 gives types away.** `B(i){...}` is a function taking `int` and
  returning `int`, and `read`, `printf`, `strtol` need no `#include` at all.

## The language

Supported: `def f():` and `f()` (no arguments, no return value) - `for v in
range(a[,b[,c]]):` - `while cond:` - `if cond:` / `else:` - `print(expr)` and
`print("literal")` - `v = expr` - integers, `+ - * / // %`, `== != < <= > >=`,
parentheses, leading `-` - `#` comments, blank lines, arbitrary nesting.

Not supported: arguments, return values, `elif`, `and`/`or`/`not`, strings as
values, lists, dicts, floats, imports, `break`/`continue`, local scope.

Limitations of the golfed versions (v4+), all deliberate:

- An identifier is its **first letter**: `total` and `t` are the same variable,
  and a function and a variable may not share a first letter.
- A statement is dispatched on its first byte, so a statement may not *begin*
  with an identifier starting `d`, `e`, `f`, `i`, `p` or `w`
  (`total = 1` is fine, `pos = 1` is not).
- Integer arithmetic only; `/` truncates like C, so `//` and `/` agree.
- Comparisons yield `1`/`0`, not `True`/`False`.
- Indentation must be spaces, line endings LF, identifiers lowercase.
- A `"` inside a `#` comment confuses the loader.
- v10/v11 additionally drop `while`, `range` steps, parentheses, comments,
  assignment and every comparison but `==` - exactly what FizzBuzz needs.

## Layout

```
program.py        the FizzBuzz that has to work
src/pygolf_v1.c   readable reference, fully commented - start here
src/pygolf_v9.c   the 1021-byte full-subset version
src/pygolf_v11.c  the 644-byte FizzBuzz version, one line
bin/pygolf        prebuilt v9   (x86-64 Linux)
bin/pygolf-min    prebuilt v11  (x86-64 Linux)
tests/            programs whose output must match CPython exactly
run_tests.sh      builds every version and diffs it against python3
```

```sh
./run_tests.sh          # the whole ladder
make                    # bin/pygolf and bin/pygolf-min
```

**Author: Marcel Petrick <mail@marcelpetrick.it>** - License: GPLv3 or later.
**Note: project is generated with AI.**
