# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Workload C: 20 small Python tasks and the unit-test checker.

The checker runs the answer in a separate ``python -I`` process with a timeout. It never imports
model output into this process.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Task:
    """One task: the prompt and the assertions that decide pass or fail."""

    task_id: str
    prompt: str
    tests: str


TASKS: tuple[Task, ...] = (
    Task("is-palindrome", "Write `is_palindrome(s: str) -> bool` that ignores case and every non-alphanumeric character.",
         "assert is_palindrome('A man, a plan, a canal: Panama')\nassert not is_palindrome('race a car')\nassert is_palindrome('')"),
    Task("run-length", "Write `rle(s: str) -> str` that run-length encodes a string, e.g. 'aaabcc' -> 'a3b1c2'.",
         "assert rle('aaabcc') == 'a3b1c2'\nassert rle('') == ''\nassert rle('x') == 'x1'"),
    Task("flatten", "Write `flatten(xs: list) -> list` that flattens arbitrarily nested lists.",
         "assert flatten([1, [2, [3, [4]]], 5]) == [1, 2, 3, 4, 5]\nassert flatten([]) == []\nassert flatten([[[]]]) == []"),
    Task("roman", "Write `to_roman(n: int) -> str` for 1 <= n <= 3999.",
         "assert to_roman(1994) == 'MCMXCIV'\nassert to_roman(4) == 'IV'\nassert to_roman(3999) == 'MMMCMXCIX'"),
    Task("from-roman", "Write `from_roman(s: str) -> int` for valid Roman numerals.",
         "assert from_roman('MCMXCIV') == 1994\nassert from_roman('IX') == 9\nassert from_roman('MMXXVI') == 2026"),
    Task("anagram-groups", "Write `group_anagrams(words: list[str]) -> list[list[str]]`. Keep each group in input order, and order the groups by the first appearance of their first word.",
         "assert group_anagrams(['eat','tea','tan','ate','nat','bat']) == [['eat','tea','ate'],['tan','nat'],['bat']]\nassert group_anagrams([]) == []"),
    Task("merge-intervals", "Write `merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]` that merges overlapping closed intervals and returns them sorted.",
         "assert merge([(1,3),(2,6),(8,10),(15,18)]) == [(1,6),(8,10),(15,18)]\nassert merge([(1,4),(4,5)]) == [(1,5)]\nassert merge([]) == []"),
    Task("primes", "Write `primes_up_to(n: int) -> list[int]` with the sieve of Eratosthenes.",
         "assert primes_up_to(30) == [2,3,5,7,11,13,17,19,23,29]\nassert primes_up_to(1) == []\nassert len(primes_up_to(10000)) == 1229"),
    Task("balanced", "Write `balanced(s: str) -> bool` that checks if (), [] and {} are balanced; other characters are ignored.",
         "assert balanced('a(b[c]{d}e)f')\nassert not balanced('(]')\nassert not balanced('((')\nassert balanced('')"),
    Task("word-freq", "Write `top_words(text: str, k: int) -> list[tuple[str, int]]`: lower-case words (letters only), sorted by count descending, then alphabetically.",
         "assert top_words('the cat and the hat and the bat', 2) == [('the', 3), ('and', 2)]\nassert top_words('', 3) == []"),
    Task("binary-search", "Write `bsearch(xs: list[int], x: int) -> int` that returns the index of the first occurrence of x in sorted xs, or -1.",
         "assert bsearch([1,2,2,2,3], 2) == 1\nassert bsearch([1,3,5], 4) == -1\nassert bsearch([], 1) == -1\nassert bsearch([5], 5) == 0"),
    Task("chunk", "Write `chunk(xs: list, n: int) -> list[list]` that splits xs into consecutive pieces of length n (the last may be shorter). Raise ValueError if n < 1.",
         "assert chunk([1,2,3,4,5], 2) == [[1,2],[3,4],[5]]\nassert chunk([], 3) == []\ntry:\n    chunk([1], 0)\n    raise SystemExit(1)\nexcept ValueError:\n    pass"),
    Task("camel-snake", "Write `camel_to_snake(s: str) -> str`, e.g. 'parseHTTPResponse' -> 'parse_http_response', 'userId' -> 'user_id'.",
         "assert camel_to_snake('parseHTTPResponse') == 'parse_http_response'\nassert camel_to_snake('userId') == 'user_id'\nassert camel_to_snake('simple') == 'simple'"),
    Task("matrix-transpose", "Write `transpose(m: list[list[int]]) -> list[list[int]]` for a rectangular matrix.",
         "assert transpose([[1,2,3],[4,5,6]]) == [[1,4],[2,5],[3,6]]\nassert transpose([]) == []"),
    Task("fib-memo", "Write `fib(n: int) -> int` with fib(0)=0, fib(1)=1, that is fast for n = 300.",
         "assert fib(0) == 0\nassert fib(10) == 55\nassert fib(300) == 222232244629420445529739893461909967206666939096499764990979600"),
    Task("dedupe", "Write `dedupe(xs: list) -> list` that removes duplicates and keeps the first occurrence order. Items are hashable.",
         "assert dedupe([3,1,3,2,1]) == [3,1,2]\nassert dedupe([]) == []"),
    Task("caesar", "Write `caesar(s: str, k: int) -> str` that shifts ASCII letters by k (keep case, wrap around, other characters unchanged; k may be negative).",
         "assert caesar('Hello, World!', 3) == 'Khoor, Zruog!'\nassert caesar('abc', -1) == 'zab'\nassert caesar('Zz', 27) == 'Aa'"),
    Task("digits-sum", "Write `digital_root(n: int) -> int` that repeatedly sums the decimal digits of a non-negative n until one digit remains.",
         "assert digital_root(493193) == 2\nassert digital_root(0) == 0\nassert digital_root(9) == 9"),
    Task("parse-duration", "Write `parse_duration(s: str) -> int` that converts strings like '1h30m', '45s', '2h5s' to seconds. Raise ValueError on an empty or invalid string.",
         "assert parse_duration('1h30m') == 5400\nassert parse_duration('45s') == 45\nassert parse_duration('2h5s') == 7205\nfor bad in ['', 'abc', '5x']:\n    try:\n        parse_duration(bad)\n        raise SystemExit(1)\n    except ValueError:\n        pass"),
    Task("spiral", "Write `spiral(m: list[list[int]]) -> list[int]` that returns the elements of a rectangular matrix in clockwise spiral order.",
         "assert spiral([[1,2,3],[4,5,6],[7,8,9]]) == [1,2,3,6,9,8,7,4,5]\nassert spiral([[1,2,3,4],[5,6,7,8]]) == [1,2,3,4,8,7,6,5]\nassert spiral([]) == []"),
)

TASK_BY_ID = {task.task_id: task for task in TASKS}
_BLOCK = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


def extract_code(answer: str) -> str:
    """Return the first fenced code block, or the whole answer if there is no fence."""
    match = _BLOCK.search(answer)
    return match.group(1) if match else answer


def check(task_id: str, answer: str, timeout_s: float = 10.0) -> bool:
    """Run the task's assertions against the answer in a separate process."""
    task = TASK_BY_ID[task_id]
    program = extract_code(answer) + "\n\n" + task.tests + "\n"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "candidate.py"
        path.write_text(program, encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, "-I", str(path)],
                cwd=tmp,
                capture_output=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False
    return result.returncode == 0
