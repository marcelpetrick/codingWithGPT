# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""A fake engine on 127.0.0.1 that speaks both the Ollama and the OpenAI streaming protocol.

``FakeEngine.mode`` selects the behaviour: ok, empty, http500, nousage, thinking, error, nodone.
The answer is ``FakeEngine.answer``, sent in three chunks.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class FakeEngine:
    """Start with ``with FakeEngine() as fake:``; ``fake.url`` is the base URL."""

    def __init__(self) -> None:
        self.mode = "ok"
        self.answer = (
            "```python\ndef is_palindrome(s):\n"
            "    t = [c.lower() for c in s if c.isalnum()]\n    return t == t[::-1]\n```"
        )
        self.requests: list[dict[str, Any]] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                pass

            def do_GET(self) -> None:
                if self.path == "/api/version":
                    self._send(200, b'{"version": "9.9.9"}', "application/json")
                else:
                    self._send(404, b"{}", "application/json")

            def do_POST(self) -> None:
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.requests.append({"path": self.path, "body": body})
                if self.path == "/api/generate":
                    self._send(200, b"{}", "application/json")
                elif fake.mode == "http500":
                    self._send(500, b'{"error": "model refused"}', "application/json")
                elif self.path == "/api/chat":
                    self._send(200, fake.ollama_stream(), "application/x-ndjson")
                elif self.path.endswith("/chat/completions"):
                    self._send(200, fake.openai_stream(), "text/event-stream")
                else:
                    self._send(404, b"{}", "application/json")

            def _send(self, code: int, payload: bytes, kind: str) -> None:
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def chunks(self) -> list[str]:
        if self.mode == "empty":
            return []
        third = len(self.answer) // 3
        return [self.answer[:third], self.answer[third : 2 * third], self.answer[2 * third :]]

    def ollama_stream(self) -> bytes:
        lines: list[dict[str, Any]] = []
        if self.mode == "error":
            lines.append({"error": "boom"})
        if self.mode == "thinking":
            lines.append({"message": {"role": "assistant", "content": "", "thinking": "hmm"}})
        lines += [{"message": {"role": "assistant", "content": c}, "done": False} for c in self.chunks()]
        if self.mode != "nousage":
            lines.append(
                {
                    "message": {"role": "assistant", "content": ""},
                    "done": True,
                    "prompt_eval_count": 120,
                    "eval_count": 30,
                    "eval_duration": 1000,
                    "prompt_eval_duration": 500,
                }
            )
        return "".join(json.dumps(line) + "\n" for line in lines).encode()

    def openai_stream(self) -> bytes:
        events: list[str] = [": keep-alive"]
        if self.mode == "error":
            events.append("data: " + json.dumps({"error": {"message": "boom"}}))
        if self.mode == "thinking":
            events.append("data: " + json.dumps({"choices": [{"delta": {"reasoning_content": "hmm"}}]}))
        events += ["data: " + json.dumps({"choices": [{"delta": {"content": c}}]}) for c in self.chunks()]
        if self.mode != "nousage":
            usage = {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}
            events.append("data: " + json.dumps({"choices": [], "usage": usage, "timings": {"x": 1}}))
        if self.mode != "nodone":
            events.append("data: [DONE]")
        return "".join(e + "\n\n" for e in events).encode()

    def __enter__(self) -> FakeEngine:
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
