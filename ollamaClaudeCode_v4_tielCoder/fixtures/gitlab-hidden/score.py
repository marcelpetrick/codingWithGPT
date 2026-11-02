#!/usr/bin/env python3
"""Prints "green=<0|1>" and "<k>/15" for the final issue state: score.py <work> <state.json>."""
import json, re, sys
from pathlib import Path
init = json.loads((Path(__file__).parent / "initial.json").read_text())
s = json.load(open(sys.argv[2]))
by = {x["iid"]: x for x in s["issues"]}
start = {x["iid"]: x for x in init["issues"]}
new = [x for x in s["issues"] if x["iid"] not in start]
csv = [x for x in new if "csv export" in x["title"].lower()]
c = csv[0] if len(csv) == 1 else {}
i = lambda n: by.get(n, {})
checks = [
 i(15).get("milestone") == "Sprint 42", i(15).get("assignee") == "dave", i(15).get("estimate") == 480,
 i(12).get("state") == "closed", any(re.search(r"#?\b11\b", n) for n in i(12).get("notes", []) if not n.startswith("/")),
 i(11) == start[11],
 len(csv) == 1 and len(new) == 1, "feature" in c.get("labels", []), c.get("milestone") == "Sprint 42", c.get("assignee") == "erin",
 "prio-high" in i(14).get("labels", []) and "prio-low" not in i(14).get("labels", []), i(14).get("milestone") == "",
 i(17).get("assignee") == "carol" and {"ci", "bug", "prio-high"} <= set(i(17).get("labels", [])),
 i(16).get("state") == "closed",
 i(18) == start[18] and i(19) == start[19],
]
print("green=%d" % int(s["issues"] != init["issues"]))
print("%d/%d" % (sum(map(bool, checks)), len(checks)))
