# Prior art: `python1024`, and how this repository differs

Background notes for [README.md](README.md). Everything below was checked on
**2026-09-08**, after the interpreters in this repository were finished.

## Where the challenge came from

The screenshot that started this
([`input_python1024running.png`](input_python1024running.png)) shows
`wc python1024.c` reporting 1024 bytes, `gcc-16 -std=gnu89 -w`, and
`./a.out < fizzbuzz.py` printing FizzBuzz. It turns out to be:

| | |
|---|---|
| Post | [Making a Python interpreter in 1024 bytes](https://austinhenley.com/blog/python1024.html) |
| Author | Austin Z. Henley - Principal Applied Scientist, Microsoft (Excel Agent Science) |
| Date | 6 September 2026 |
| Hacker News | [item 49591876](https://news.ycombinator.com/item?id=49591876), 315 points, ~119 comments when checked |
| Source | [AZHenley/python1024](https://github.com/AZHenley/python1024) (MIT; also ships a ~4800-byte readable version) |
| Build | `gcc-16 -std=gnu89 -w python1024.c` - GCC only, Clang will not build it |

He aimed at 512 bytes first and could not fit the language into it, so the
published result is exactly 1024 bytes.

**Provenance of this repository:** only the screenshot was known while the
interpreters here were written. The post, the discussion and his source were
read afterwards, to write this comparison. No code was taken from it.

## Two different machines

Both projects read a Python program on stdin and interpret it. Underneath they
are not the same design.

**python1024** is a recursive-descent parser that *executes directly off the
source text* - no tokenizer, no AST, no bytecode. A loop repeats by "jumping
backwards and reparsing the source each iteration". A function definition
stores its position in the symbol table; a call saves the caller's position,
jumps to the body, runs it, and restores the position afterwards. Indentation
is handled through the C call stack.

**pygolf** normalizes first. One pass over the buffer deletes every space
outside a string, drops comments and blank lines, and records each line's
indent, producing a line table. After that a block is an *index range*: a
compound statement owns the following lines indented deeper than itself, so
running a body is `X(lo, hi)` and a loop simply re-runs that range. Expressions
use one precedence-climbing loop where an operator's index in `"=!<>+-*/%"`
yields both its precedence and its operation. The four stages are described in
[README.md](README.md).

The practical difference: he re-parses the *source*, this re-runs a *line
range*. His approach needs no line table and no indent array; this one needs no
position save/restore, and gets constant offsets (`print(` is always `T[i]+6`)
out of the normalization pass.

## Feature differences

Neither subset contains the other, so 1024 against 959 is not a head-to-head.

| Feature | python1024 | pygolf v13 |
|---|---|---|
| `while ... else`, `for ... else` | yes | no |
| Recursive function calls | yes | yes |
| `for x in range(...)` | one argument | one, two or three |
| Parentheses in expressions | no | yes |
| `/` and `//` | no | yes |
| `!=` | no | yes |
| `+ - * %`, `< > <= >= ==` | yes | yes |
| Zero-argument `def`, calls, `print`, comments, indent blocks | yes | yes |
| Single-letter integer variables | yes | yes (first letter of any name) |
| Bytes | 1024 | 959 (full subset), 622 (FizzBuzz-only build) |

## Golf tricks: shared, and not

Arrived at independently on both sides: first-letter keyword matching,
single-letter identifiers, C89 implicit `int`, ASCII codes instead of character
literals, ternary and comma operators folding statements into expressions,
bitwise operators standing in for logical ones, and zero-initialized globals.
Given one compiler and one target, the same tricks are hard to miss.

Particular to python1024: loops as backward jumps into the source, caller
position save/restore for calls, and reusing function parameters as temporaries
that survive a call.

Particular to pygolf: the normalization pass that makes keyword offsets
constant; unary minus falling out of an always-zero variable slot; `<=` folded
into `<` as `v < x+1`; the closing quote overwritten with `\0` so a `print`
line begins with `\0` exactly when its argument is a string; `default` placed
first in the `switch` so all five remaining labels share a `break;case ` macro.

## One divergence worth naming

Recursion works here, which the design does not make obvious - a call runs the
function's line range, and the C stack does the rest:

```python
def count():
    print(n)
    n = n - 1
    if n > 0:
        count()
    else:
        print("liftoff")


n = 3
count()
```

```
$ ./bin/pygolf < recursion.py
3
2
1
liftoff
```

CPython **rejects this exact program** with `UnboundLocalError`: assigning `n`
inside the function makes it local, and it would need `global n`. Every
variable here is global, so this is a semantic divergence rather than a missing
feature - which is why it is not in `tests/`, where every program must produce
exactly what CPython produces.
