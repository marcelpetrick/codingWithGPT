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
            out = run([str(exe)], tree, 60).stdout
            k = len([m for m in re.findall(r"^PASS\s*:\s*TstHidden::(\w+)\(\)", out, re.M) if m not in ("initTestCase", "cleanupTestCase")])
print(f"green={green}")
print(f"{k}/{N}")
