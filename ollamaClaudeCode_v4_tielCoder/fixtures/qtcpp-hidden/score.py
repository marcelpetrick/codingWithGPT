#!/usr/bin/env python3
"""Prints "green=<0|1>" and "<k>/14" for a qtcpp working tree. Works on a copy."""
import os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
N = 14
# ~/.local/bin/ctest is a broken pip shim on this laptop; the system tools must win.
os.environ["PATH"] = "/usr/bin:" + os.environ.get("PATH", "")
HERE = Path(__file__).resolve().parent
def run(cmd, cwd, timeout=300):
    try:
        return subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "")
work = Path(sys.argv[1])
with tempfile.TemporaryDirectory() as t:
    tree = Path(t) / "tree"
    shutil.copytree(work, tree, ignore=shutil.ignore_patterns("build", ".git"))
    shutil.copytree(HERE, tree / "hidden", ignore=shutil.ignore_patterns("score.py", "__pycache__"))
    with (tree / "CMakeLists.txt").open("a") as f:
        f.write("\nadd_subdirectory(hidden)\n")
    b = tree / "b"
    ok = run(["cmake", "-S", ".", "-B", "b", "-G", "Ninja"], tree).returncode == 0
    green = 0; k = 0
    if ok:
        run(["cmake", "--build", "b"], tree)
        env_v = run(["ctest", "--test-dir", "b", "--output-on-failure", "-R", "tst_backlog"], tree)
        green = int(env_v.returncode == 0 and (b / "tests" / "tst_backlog").exists())
        exe = b / "hidden" / "tst_hidden"
        if exe.exists():
            # One process per test: a crash in one test must not cost the tests after it.
            names = [l.split("(")[0] for l in run([str(exe), "-functions"], tree, 30).stdout.splitlines() if l.endswith("()")]
            if len(names) != N:
                sys.exit(f"score.py: expected {N} hidden tests, found {len(names)}")
            for name in names:
                r = run([str(exe), name], tree, 30)
                k += int(r.returncode == 0 and re.search(rf"^PASS\s*:\s*TstHidden::{name}\(\)", r.stdout, re.M) is not None)
print(f"green={green}")
print(f"{k}/{N}")
