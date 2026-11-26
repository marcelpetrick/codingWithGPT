# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""A fake Ollama REST server with a rule-based stub classifier.

The stub is not a language model. It exists so that tests and the offline demo run without the
real server. Every result it produces carries the model name "stub-rules".
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

STUB_MODEL = "stub-rules"
_THREAD = re.compile(r"<thread_json>\n(.*)\n</thread_json>", re.DOTALL)

_FIX = re.compile(r"fixed|korrigiert|corrigé|done|changed it|textcontent|docs are", re.IGNORECASE)


def _intent(text: str) -> tuple[str, str]:
    t = text.lower()
    if t.startswith("nit"):
        return "style", "optional_suggestion"
    rules = [
        (("token", "sql"), "security"),
        (
            (
                "null",
                "crash",
                "underflow",
                "use-after-free",
                "off-by-one",
                "nullptr",
                "millisekunden",
                "vide",
                "swallowed",
                "hides the exception",
            ),
            "defect",
        ),
        (("singleton", "free function", "mutex", "approach", "std::span"), "design"),
        (("test",), "test"),
        (("o(n", "duplicated", "split", "document"), "maintainability"),
    ]
    for keys, intent in rules:
        if any(k in t for k in keys):
            return intent, "change_request"
    if "?" in t:
        return "clarification", "question"
    return "other", "change_request"


def stub_classify(thread: dict[str, Any]) -> dict[str, Any]:
    """Classify a thread with keyword rules (for tests and the offline demo only)."""
    notes = thread["notes"]
    if not notes:
        return {"findings": []}
    first = notes[0]
    intent, action = _intent(first["text"])
    replies = notes[1:]
    responses: list[dict[str, Any]] = []
    outcome, validity, tone, primary = "open", "indeterminate", "neutral", "none_observed"
    decision: int | None = None
    ref: str | None = None
    for r in replies:
        t = r["text"]
        tl = t.lower()
        act = "acknowledgement"
        if "instead" in tl:
            act, outcome, validity = "alternative_proposal", "alternative_claimed", "supported"
        elif "added the overflow" in tl:
            act, outcome, validity = "partial_agreement", "partial_claimed", "partially_supported"
        elif "out of scope" in tl:
            act, outcome, validity = "deferral", "deferred", "supported"
            m = re.search(r"#\d+", t)
            ref = m.group(0) if m else None
        elif "we need exactly" in tl or "c++17" in tl:
            act, outcome, validity = "reasoned_disagreement", "justified_no_change", "rebutted"
        elif "rather keep" in tl:
            act, outcome = "reasoned_disagreement", "optional_declined"
        elif "so no" in tl:
            act, outcome, tone = "unsupported_rejection", "declined_unjustified", "dismissive"
        elif "will fix" in tl or "working on it" in tl:
            act, outcome = "acknowledgement", "promised"
        elif "fall back" in tl or "see the branch" in tl:
            act, outcome, validity = "explanation", "justified_no_change", "rebutted"
        elif _FIX.search(t):
            act, outcome, validity = "agreement", "implemented_claimed", "supported"
        elif "agreed" in tl or "makes sense" in tl or "enabled c++20" in tl:
            act = "agreement"
            if "enabled" in tl:
                act, outcome, validity = "explanation", "open", "supported"
        if (
            any(w in tl for w in ("thanks", "good catch", "merci", "🙏", "fair point"))
            and tone == "neutral"
        ):
            tone = "appreciative"
        responses.append({"note_id": r["id"], "act": act})
        if act != "acknowledgement" or outcome == "promised":
            decision = r["id"]
    if responses:
        primary = responses[0]["act"]
    if "this whole approach is wrong" in first["text"].lower():
        tone = "dismissive"
    abstain = "ignore all previous instructions" in first["text"].lower()
    finding = {
        "summary": first["text"][:120],
        "intent": intent,
        "actionability": action,
        "validity": validity,
        "responses": responses,
        "primary_response": primary,
        "tone": tone,
        "criticism_target": "code",
        "text_outcome": "unknown" if abstain else outcome,
        "deferral_ref": ref,
        "decision_note_id": decision,
        "evidence_note_ids": [n["id"] for n in notes[:3]],
        "rationale": f"Rule-based stub: first note {first['id']} read as {intent}; "
        f"{len(replies)} replies.",
        "abstain": abstain,
    }
    return {"findings": [finding]}


class FakeOllama:
    """Serve /api/version, /api/tags and /api/chat. faults is a list of modes used in order."""

    def __init__(self, model: str = STUB_MODEL) -> None:
        self.model = model
        self.faults: list[str] = []
        self.calls = 0
        self.bodies: list[dict[str, Any]] = []
        self.lock = threading.Lock()

    def handle(self, method: str, path: str, body: bytes) -> tuple[int, bytes]:
        if path == "/api/version":
            return 200, b'{"version":"0.0.0-fake"}'
        if path == "/api/tags":
            return (
                200,
                json.dumps(
                    {"models": [{"name": self.model, "model": self.model, "digest": "f" * 64}]}
                ).encode(),
            )
        if path != "/api/chat" or method != "POST":
            return 404, b'{"error":"not found"}'
        req = json.loads(body)
        with self.lock:
            self.calls += 1
            self.bodies.append(req)
            fault = self.faults.pop(0) if self.faults else ""
        if req.get("model") != self.model:
            return 404, json.dumps({"error": f"model '{req.get('model')}' not found"}).encode()
        if fault == "500":
            return 500, b'{"error":"boom"}'
        if fault == "notjson":
            return 200, b"<html>proxy error</html>"
        if fault == "badmessage":
            return 200, b'{"message": "oops"}'
        if fault == "nomessage":
            return 200, b'{"done":true}'
        if fault == "length":
            return 200, json.dumps({"message": {"content": "{"}, "done_reason": "length"}).encode()
        m = _THREAD.search(req["messages"][-1]["content"])
        thread = json.loads(m.group(1))["thread"] if m else {"notes": []}
        result = stub_classify(thread)
        content = json.dumps(result, ensure_ascii=False)
        if fault == "malformed":
            content = content[:40]
        elif fault == "bad_enum":
            result["findings"][0]["intent"] = "bug"
            content = json.dumps(result)
        return (
            200,
            json.dumps(
                {
                    "model": self.model,
                    "message": {"role": "assistant", "content": content},
                    "done": True,
                    "done_reason": "stop",
                    "eval_count": 42,
                }
            ).encode(),
        )


def _handler(fake: FakeOllama) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _serve(self) -> None:
            length = int(self.headers.get("content-length") or 0)
            status, body = fake.handle(self.command, self.path, self.rfile.read(length))
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = _serve
        do_POST = _serve

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


@contextmanager
def serve(fake: FakeOllama) -> Iterator[str]:
    """Run the fake Ollama on a free local port; yield its base URL."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(fake))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
