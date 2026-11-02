"""Tests for refresh-compare.py: each void case is a defect that once looked like a result."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("rc", Path(__file__).with_name("refresh-compare.py"))
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

HEAD = "date ollama model fixture thinking run verdict hidden wall_s warm_s calls turns in_tok out_tok think_chars api_s ttft_s max_gap_s tools reloads foreign note".split()
SHEAD = "model run phase ollama score words prompt_tok prefill_s prefill_tps gen_tok gen_tps wall_s void missed".split()
M = "kat:x"
TOTAL = {"hard": 18, "qtcpp": 14, "gitlab": 15}


def add(res, tag=M, fx="hard", run=1, k=None, wall=40, foreign="-", reloads=0, note="", vram=None, result=True, err=False, ollama="0.40.11", arm="a"):
    (res / "cc").mkdir(exist_ok=True)
    f = res / f"cc-session-{arm}.tsv"
    if not f.exists():
        f.write_text("\t".join(HEAD) + "\n")
    n = TOTAL[fx]
    vals = ["d", ollama, tag, fx, "on", run, "PASS", f"{n if k is None else k}/{n}", wall, 1, 1, 1, 100, 1, 1, 1, 1, 1, "t", reloads, foreign, note]
    with f.open("a") as h:
        h.write("\t".join(map(str, vals)) + "\n")
    base = f"{rc.safe(tag)}-{fx}-thinkon-{arm}-r{run}"
    (res / "cc" / f"{base}.ps.tsv").write_text(f"1\t{tag}|100|{100 if vram is None else vram}|262144|x\n")
    ev = {"type": "result", "is_error": err} if result else {"type": "system"}
    (res / "cc" / f"{base}.jsonl").write_text(json.dumps(ev) + "\n")


def add_summary(res, tag=M, run=1, k=16, words=400, void="", arm="a"):
    f = res / f"summary-{arm}.tsv"
    if not f.exists():
        f.write_text("\t".join(SHEAD) + "\n")
    phase = {1: "cold", 2: "repeat", 3: "extend"}[run]
    vals = [tag, run, phase, "0.40.11", f"{k}/16", words, 150000, 60, 2500, 500, 100, 70, void, ""]
    with f.open("a") as h:
        h.write("\t".join(map(str, vals)) + "\n")


def full(res, tag, wall=40, k=None, runs=3):
    for r in range(1, runs + 1):
        for fx in rc.SESSIONS:
            add(res, tag=tag, fx=fx, run=r, wall=wall, k=k)
        add_summary(res, tag=tag, run=r)


def reason(res, fx="hard", run=1):
    return rc.void_reason(rc.rows("a", res).get((M, fx, run)), M, fx, run, "a", res)


def test_clean_run_counts(tmp_path):
    add(tmp_path)
    assert reason(tmp_path) is None


@pytest.mark.parametrize("kw,word", [
    ({"vram": 50}, "spilled"), ({"foreign": "other:1"}, "foreign"), ({"reloads": 1}, "reloaded"),
    ({"result": False}, "no result"), ({"err": True}, "error"), ({"ollama": "?"}, "version")])
def test_bad_runs_are_void(tmp_path, kw, word):
    add(tmp_path, **kw)
    assert word in reason(tmp_path)


def test_model_never_resident_is_void(tmp_path):
    add(tmp_path)
    (tmp_path / "cc" / "kat_x-hard-thinkon-a-r1.ps.tsv").write_text("1\t-\n")
    assert "never resident" in reason(tmp_path)


def test_timeout_is_a_result(tmp_path):
    add(tmp_path, result=False, note="timeout after 600s")
    assert reason(tmp_path) is None


def test_rerun_replaces_void_row(tmp_path):
    add(tmp_path, foreign="other:1")
    add(tmp_path, wall=50)
    assert rc.summarize("a", tmp_path)[M]["walls"]["hard"] == [50.0]


def test_void_summary_is_not_a_low_score(tmp_path):
    add_summary(tmp_path, k=0, void="empty answer")
    e = rc.summarize("a", tmp_path)[M]
    assert e["tasks"]["summary"] == [] and "empty answer" in e["void"][0]


def test_overlong_summary_scores_zero(tmp_path):
    add_summary(tmp_path, words=601)
    assert rc.summarize("a", tmp_path)[M]["tasks"]["summary"] == [0.0]


def test_correctness_is_mean_of_task_medians(tmp_path):
    full(tmp_path, M)
    for r in (1, 2, 3):
        add(tmp_path, fx="gitlab", run=r, k=0)
    assert rc.summarize("a", tmp_path)[M]["correct"] == 75.0


def gate(res, *pairs):
    (res / "gate-rerun.tsv").write_text("".join(f"{t}\tT5\t{v}\tx\n" for t, v in pairs))


def test_ranking_prefers_correct_over_fast(tmp_path):
    full(tmp_path, "right", wall=90)
    full(tmp_path, "quick", wall=10, k=9)
    gate(tmp_path, ("right", "8/8"), ("quick", "8/8"))
    assert rc.ranking(rc.summarize("a", tmp_path)) == ["right", "quick"]


def test_tie_within_three_points_goes_by_speed(tmp_path):
    full(tmp_path, "right", wall=90)
    full(tmp_path, "quick", wall=10)
    for r in (1, 2, 3):
        add(tmp_path, tag="quick", fx="hard", run=r, wall=10, k=16)  # 88.9% on one task of four
    gate(tmp_path, ("right", "8/8"), ("quick", "8/8"))
    by = rc.summarize("a", tmp_path)
    assert 100 - by["quick"]["correct"] <= 3
    assert rc.ranking(by) == ["quick", "right"]


def test_t5_gate_and_low_n_are_not_ranked(tmp_path):
    full(tmp_path, "flaky")
    full(tmp_path, "short", runs=1)
    full(tmp_path, "ok")
    gate(tmp_path, ("flaky", "6/8"), ("short", "8/8"), ("ok", "7/8"))
    assert rc.ranking(rc.summarize("a", tmp_path)) == ["ok"]


def test_report_names_pick_speed_and_drift(tmp_path):
    full(tmp_path, rc.CONTROL, wall=50)
    for i in range(1, 4):
        add(tmp_path, tag=rc.CONTROL, run=i, wall=40, arm="rb1019")
    gate(tmp_path, (rc.CONTROL, "8/8"))
    t = rc.report("a", tmp_path)
    assert "Pick by the rule: " + rc.CONTROL in t and "+25%" in t and "Outside 5%" in t and "| 2500 |" in t


def test_two_rounds_are_preliminary(tmp_path):
    full(tmp_path, M, runs=2)
    gate(tmp_path, (M, "8/8"))
    assert "preliminary, n=2" in rc.report("a", tmp_path)
