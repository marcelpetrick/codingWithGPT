#!/usr/bin/env python3
"""Compare the no-think template with Ollama's qwen3.8 renderer at think=false.

Both prompts come from the box with _debug_render_only, so no model loads.
Usage: render_check.py HOST STOCK_TAG TEMPLATE_TAG
Exit 0 = identical apart from the tool-JSON spacing (the one known difference).
"""
import difflib, json, sys, urllib.request

TOOLS = [{"type": "function", "function": {"name": "Edit", "description": "Edit a file.\nKeep \"quotes\".",
          "parameters": {"type": "object", "required": ["file_path", "old_string"],
                         "properties": {"file_path": {"type": "string", "description": "path"},
                                        "old_string": {"type": "string"},
                                        "replace_all": {"type": "boolean"},
                                        "edits": {"type": "array", "items": {"type": "object"}}}}}},
         {"type": "function", "function": {"name": "Bash", "description": "Run a command.",
          "parameters": {"type": "object", "required": ["command"],
                         "properties": {"command": {"type": "string"}, "timeout": {"type": "number"}}}}}]
MSGS = [
    {"role": "system", "content": "You are Claude Code."},
    {"role": "user", "content": "Fix the bug in a.py."},
    {"role": "assistant", "content": "I will look first.", "tool_calls": [
        {"function": {"name": "Bash", "arguments": {"command": "cat a.py\nls -l", "timeout": 30}}},
        {"function": {"name": "Edit", "arguments": {"file_path": "a.py", "old_string": "x = 1",
                                                     "replace_all": False, "edits": [{"a": 1}]}}}]},
    {"role": "tool", "content": "x = 1\n-rw a.py"},
    {"role": "tool", "content": "edited"},
    {"role": "system", "content": "<system-reminder>mid-conversation</system-reminder>"},
    {"role": "assistant", "content": "", "tool_calls": [
        {"function": {"name": "Bash", "arguments": {"command": "pytest -q"}}}]},
    {"role": "tool", "content": "1 passed"},
    {"role": "assistant", "content": "Done."},
    {"role": "user", "content": "Thanks. Now explain."},
]


def render(host, model, think):
    body = {"model": model, "messages": MSGS, "tools": TOOLS, "stream": False, "_debug_render_only": True}
    if think is not None:
        body["think"] = think
    req = urllib.request.Request(f"http://{host}:11434/api/chat", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["_debug_info"]["rendered_template"]


def spaced(s):
    """Normalise the one known difference: compact vs Python-style tool JSON."""
    return s.replace('","', '", "').replace('":', '": ').replace(',"', ', "').replace('":  ', '": ')


def main(host, stock, tmpl):
    a = render(host, stock, False)
    # The template tag has no thinking capability: /api/chat refuses think=true with 400,
    # and the Anthropic route (Claude Code) relaxes it to nil. So nil is what Claude Code gets.
    b_true = render(host, tmpl, None)
    if b_true != render(host, tmpl, False):
        print("FAIL: the template depends on think"); return 1
    if a == b_true:
        print("IDENTICAL"); return 0
    if spaced(a) == spaced(b_true):
        print("IDENTICAL except tool-JSON spacing"); return 0
    sys.stdout.writelines(difflib.unified_diff(a.splitlines(1), b_true.splitlines(1), "renderer", "template"))
    return 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
