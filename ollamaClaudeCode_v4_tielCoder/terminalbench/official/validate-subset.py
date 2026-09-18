#!/usr/bin/env python3
"""validate-subset.py -- can a model that follows the instruction exactly pass?

Written after `nginx-request-logging` scored 0/12 in the 2026-09-18 round. That
task was not hard; it was *underspecified*. Its instruction says

    Place the configuration in /etc/nginx/conf.d/benchmark-site.conf

while its test reads /etc/nginx/nginx.conf and requires a log format named
literally "detailed" -- a filename and a string that appear nowhere in the
instruction. Every model wrote a correct config in the file it was told to use,
passed 7 of 8 sub-tests, and failed. No model could have passed it.

This is static analysis, not a run: it extracts the literals a task's tests
demand (absolute paths and quoted strings used in assertions) and reports the
ones the instruction never mentions. A hit is not proof of a defect -- a test may
legitimately check an implementation detail a competent answer implies -- but
every hit is a question worth answering BEFORE a subset is frozen, because after
that the comparison is spent.

Usage:
  ./validate-subset.py                # every task in subset.txt
  ./validate-subset.py <task> [...]   # named tasks, e.g. a candidate replacement
"""
import ast
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASET = Path.home() / ".cache/terminal-bench/terminal-bench-core/0.1.1"

# Literals that are ubiquitous shell/python noise rather than task requirements.
IGNORE = re.compile(
    r"^(|/|\.|\.\.|/app|/tmp|/root|utf-8|r|w|rb|wb|a|\n|\t| |,|:|;|\||-|=|/bin/bash|"
    r"/bin/sh|python3?|bash|sh|true|false|None|__main__|localhost|0\.0\.0\.0)$")


def instruction(task):
    y = (DATASET / task / "task.yaml").read_text()
    m = re.search(r"^instruction:\s*\|-?\n(.*?)(?=^\w+:)", y, re.S | re.M)
    return (m.group(1) if m else y).casefold()


def test_literals(task):
    """Literals a test COMPARES against, never its failure message.

    Parsed with `ast` rather than grepped: `assert cond, "message"` puts human
    prose in .msg, and matching that produced nothing but noise. Only .test is
    read, so what comes back is what the task actually demands.
    """
    out = set()
    for f in sorted((DATASET / task / "tests").glob("*.py")):
        try:
            tree = ast.parse(f.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            # the condition of an assert, and nothing else
            subtrees = []
            if isinstance(node, ast.Assert):
                subtrees.append(node.test)
            elif isinstance(node, ast.Assign):
                # `formats = ["log_format", "detailed", ...]` and
                # `config_files = ["/etc/nginx/nginx.conf"]` -- nginx's real defect
                # lives here, checked by a later loop rather than inside the assert,
                # which is exactly why the first version of this script missed it.
                if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                    subtrees.append(node.value)
            elif isinstance(node, ast.Call):
                fn = node.func
                name = getattr(fn, "attr", None) or getattr(fn, "id", None)
                if name in {"search", "match", "fullmatch", "findall", "read_text",
                            "exists", "is_file", "is_dir", "Path", "open", "get"}:
                    subtrees.extend(node.args)
            for sub in subtrees:
                for lit in ast.walk(sub):
                    if isinstance(lit, ast.Constant) and isinstance(lit.value, str):
                        v = lit.value.strip()
                        # a requirement is a token, a path or a regex -- not a sentence
                        if len(v) < 3 or IGNORE.match(v):
                            continue
                        if v.count(" ") >= 3:
                            continue
                        out.add(v)
    return out


def main():
    tasks = sys.argv[1:]
    if not tasks:
        tasks = [l.strip() for l in (HERE / "subset.txt").read_text().splitlines()
                 if l.strip() and not l.startswith("#")]
    worst = 0
    for t in tasks:
        if not (DATASET / t).is_dir():
            print(f"{t}: NOT IN DATASET"); continue
        instr = instruction(t)
        missing = sorted(s for s in test_literals(t) if s.casefold() not in instr)
        flag = "OK " if not missing else f"{len(missing):>2} UNSTATED"
        print(f"{flag}  {t}")
        for s in missing:
            print(f"        demanded by the tests, absent from the instruction: {s!r}")
        worst = max(worst, len(missing))
    print("\nA hit is a question, not a verdict: check whether a correct answer to the "
          "instruction\nnecessarily produces it. If it does not, the task cannot be passed "
          "as written.")
    return 1 if worst else 0


if __name__ == "__main__":
    sys.exit(main())
