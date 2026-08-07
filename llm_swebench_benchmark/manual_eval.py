#!/usr/bin/env python3
"""
Manually evaluate SWE-bench predictions using venvs and fuzzy patch application.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def clone_repo(repo: str, commit: str, tmp_dir: str) -> str:
    repo_dir = os.path.join(tmp_dir, repo.replace("/", "__"))
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    subprocess.run(
        ["git", "clone", "--quiet", f"https://github.com/{repo}.git", repo_dir],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "--quiet", commit],
        cwd=repo_dir, check=True, capture_output=True,
    )
    return repo_dir


def apply_patch(repo_dir: str, patch: str) -> tuple[bool, str]:
    """Apply patch with fuzz. Returns (success, error_msg)."""
    if not patch:
        return False, "empty patch"
    # Try exact first
    result = subprocess.run(
        ["git", "apply", "--check", "-C10"],
        cwd=repo_dir, input=patch, text=True, capture_output=True, timeout=30,
    )
    if result.returncode == 0:
        result = subprocess.run(
            ["git", "apply", "-C10"],
            cwd=repo_dir, input=patch, text=True, capture_output=True, timeout=30,
        )
        return result.returncode == 0, str(result.stderr)[:200] if result.stderr else ""
    return False, str(result.stderr)[:200]


def setup_venv(repo_dir: str) -> tuple[bool, str, str]:
    """Create venv and install deps. Returns (success, venv_path, error)."""
    venv_path = os.path.join(repo_dir, ".venv")
    # Create venv
    result = subprocess.run(
        ["python3", "-m", "venv", venv_path],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        return False, "", result.stderr[:200]

    pip = os.path.join(venv_path, "bin", "pip")
    python = os.path.join(venv_path, "bin", "python")

    # Upgrade pip
    subprocess.run([pip, "install", "--quiet", "-U", "pip"], capture_output=True, timeout=120)

    # Install pytest
    subprocess.run([pip, "install", "--quiet", "pytest"], capture_output=True, timeout=120)

    # Try installing repo deps
    req_file = os.path.join(repo_dir, "requirements.txt")
    if os.path.exists(req_file):
        subprocess.run([pip, "install", "--quiet", "-r", req_file], capture_output=True, timeout=300)

    setup_file = os.path.join(repo_dir, "setup.py")
    pyproject = os.path.join(repo_dir, "pyproject.toml")
    if os.path.exists(setup_file):
        subprocess.run([pip, "install", "--quiet", "-e", "."], capture_output=True, timeout=300)
    elif os.path.exists(pyproject):
        subprocess.run([pip, "install", "--quiet", "-e", "."], capture_output=True, timeout=300)

    return True, venv_path, ""


def run_tests(repo_dir: str, test_specs: list, venv_python: str) -> dict:
    """Run FAIL_TO_PASS tests. Returns {resolved, total, details}."""
    resolved = 0
    total = len(test_specs)
    details = []

    for spec in test_specs[:20]:  # Cap at 20 tests per instance for speed
        if "::" in spec:
            test_file, test_name = spec.split("::", 1)
        else:
            test_file = spec
            test_name = None

        test_path = os.path.join(repo_dir, test_file)
        if not os.path.exists(test_path):
            details.append({"test": spec, "status": "file_not_found"})
            continue

        cmd = [venv_python, "-m", "pytest", test_file, "-v", "--tb=short", "-x", "-q"]
        if test_name:
            cmd.append(f"::{test_name}")

        result = subprocess.run(
            cmd, cwd=repo_dir, capture_output=True, text=True, timeout=120,
        )

        passed = result.returncode == 0
        if passed:
            resolved += 1

        details.append({
            "test": spec,
            "status": "resolved" if passed else "unresolved",
        })

    return {"resolved": resolved, "total": len(details), "details": details}


def evaluate_instance(instance: dict, patch: str, tmp_dir: str) -> dict:
    iid = instance["instance_id"]
    repo = instance["repo"]
    commit = instance["base_commit"]
    fail_to_pass = instance.get("FAIL_TO_PASS", [])
    version = instance.get("version", "unknown")

    print(f"\n{'='*60}")
    print(f"Instance: {iid}")
    print(f"Repo: {repo} v{version}")

    # Clone
    print("Cloning...", file=sys.stderr)
    repo_dir = clone_repo(repo, commit, tmp_dir)

    # Setup venv
    print("Setting up venv...", file=sys.stderr)
    success, venv_path, err = setup_venv(repo_dir)
    if not success:
        return {"instance_id": iid, "status": "setup_failed", "error": err}
    venv_python = os.path.join(venv_path, "bin", "python")

    # Apply patch
    print("Applying patch...", file=sys.stderr)
    patch_ok, patch_err = apply_patch(repo_dir, patch)
    if not patch_ok:
        return {"instance_id": iid, "status": "patch_failed", "error": patch_err}

    # Run tests
    print(f"Running {len(fail_to_pass)} tests (capped at 20)...", file=sys.stderr)
    if fail_to_pass:
        results = run_tests(repo_dir, fail_to_pass, venv_python)
    else:
        results = {"resolved": 0, "total": 0, "details": []}

    status = "resolved" if results["resolved"] == results["total"] and results["total"] > 0 else "partial"
    if results["total"] == 0:
        status = "no_tests"

    print(f"  Result: {results['resolved']}/{results['total']} resolved ({status})", file=sys.stderr)

    return {
        "instance_id": iid,
        "status": status,
        "resolved": results["resolved"],
        "total": results["total"],
        "patch_applied": True,
        "details": results["details"],
    }


def main():
    parser = argparse.ArgumentParser(description="Manual SWE-bench evaluation")
    parser.add_argument("--instances", type=int, default=5, help="Number of instances")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--output", default="manual_results.json")
    parser.add_argument("--tmp_dir", default="/tmp/swebench-manual-eval")
    args = parser.parse_args()

    print("Loading predictions...", file=sys.stderr)
    with open("/tmp/swebench_benchmark/predictions_full.json") as f:
        predictions = json.load(f)

    from datasets import load_dataset
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    instance_map = {inst["instance_id"]: dict(inst) for inst in ds}

    instances_with_patches = [p for p in predictions if p.get("model_patch", "")]
    to_evaluate = instances_with_patches if args.all else instances_with_patches[:args.instances]

    print(f"Evaluating {len(to_evaluate)} instances...", file=sys.stderr)
    os.makedirs(args.tmp_dir, exist_ok=True)
    results = []
    start_time = time.time()

    for i, pred in enumerate(to_evaluate):
        iid = pred["instance_id"]
        print(f"\n[{i+1}/{len(to_evaluate)}] {iid}", file=sys.stderr)
        if iid not in instance_map:
            continue
        result = evaluate_instance(instance_map[iid], pred["model_patch"], args.tmp_dir)
        results.append(result)
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)

    elapsed = time.time() - start_time
    resolved = sum(1 for r in results if r["status"] == "resolved")
    partial = sum(1 for r in results if r["status"] == "partial")
    patch_failed = sum(1 for r in results if r["status"] == "patch_failed")
    setup_failed = sum(1 for r in results if r["status"] == "setup_failed")

    print(f"\n{'='*60}")
    print(f"Done in {elapsed:.0f}s")
    print(f"Total: {len(results)} | Resolved: {resolved} | Partial: {partial} | Patch failed: {patch_failed} | Setup failed: {setup_failed}")
    print(f"Results: {args.output}")


if __name__ == "__main__":
    main()
