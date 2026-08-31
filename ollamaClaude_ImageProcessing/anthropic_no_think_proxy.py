#!/usr/bin/env python3
"""Anthropic-compatible proxy that forces Qwen /no_think on every user turn."""

from __future__ import annotations

import argparse
import http.client
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


DIRECTIVE = "/no_think\n"
VISION_SYSTEM = "You are a precise vision and OCR assistant. Transcribe requested text exactly and describe only what is visible."
REMINDER_RE = re.compile(
    r"<(?:system-reminder|total_tokens)>.*?</(?:system-reminder|total_tokens)>",
    re.DOTALL,
)


def inject_no_think(payload: dict) -> bool:
    """Put /no_think in every real user message, where Qwen actually honors it."""
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return False
    injected = False
    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            if not content.lstrip().startswith("/no_think"):
                message["content"] = DIRECTIVE + content
                injected = True
            continue
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if not text.lstrip().startswith("/no_think"):
                        block["text"] = DIRECTIVE + text
                        injected = True
                    break
            else:
                content.insert(0, {"type": "text", "text": DIRECTIVE.rstrip()})
                injected = True
            continue
        message["content"] = DIRECTIVE.rstrip()
        injected = True
    return injected


def strip_claude_scaffolding(payload: dict) -> None:
    """Keep Claude's image UI, but remove coding-agent metadata that derails Qwen."""
    payload["system"] = VISION_SYSTEM
    payload.pop("tools", None)
    payload.pop("tool_choice", None)
    try:
        payload["max_tokens"] = min(int(payload.get("max_tokens", 4096)), 4096)
    except (TypeError, ValueError):
        payload["max_tokens"] = 4096
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return
    clean_messages = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            message["content"] = REMINDER_RE.sub("", content).strip()
            if message["content"]:
                clean_messages.append(message)
            continue
        if not isinstance(content, list):
            clean_messages.append(message)
            continue
        clean = []
        for block in content:
            if not isinstance(block, dict):
                clean.append(block)
                continue
            if block.get("type") == "thinking":
                continue
            if block.get("type") == "text":
                text = REMINDER_RE.sub("", str(block.get("text", ""))).strip()
                if not text:
                    continue
                block = dict(block)
                block["text"] = text
            clean.append(block)
        message["content"] = clean
        if clean:
            clean_messages.append(message)
    payload["messages"] = clean_messages


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    upstream_host = "127.0.0.1"
    upstream_port = 11434

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.log_date_time_string()} {fmt % args}", file=sys.stderr, flush=True)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            body = json.dumps({"ok": True, "service": "claude-vision-no-think"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._forward(None)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        injected = False
        if self.path.startswith("/v1/messages") and body:
            try:
                payload = json.loads(body)
                strip_claude_scaffolding(payload)
                injected = inject_no_think(payload)
                # Ollama honors this field even though Claude Code's third-party path
                # does not send it consistently. The user-message directive is the
                # primary fix; this is a second guard.
                payload["thinking"] = {"type": "disabled"}
                body = json.dumps(payload, separators=(",", ":")).encode()
            except (json.JSONDecodeError, TypeError):
                pass
        if injected:
            print(f"injected /no_think into {self.path}", file=sys.stderr, flush=True)
        self._forward(body)

    def _forward(self, body: bytes | None) -> None:
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "content-length", "connection", "accept-encoding"}
        }
        if body is not None:
            headers["Content-Length"] = str(len(body))
        connection = http.client.HTTPConnection(self.upstream_host, self.upstream_port, timeout=1800)
        try:
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in {"content-length", "transfer-encoding", "connection", "content-encoding"}:
                    self.send_header(key, value)
            self.send_header("Connection", "close")
            self.end_headers()
            while chunk := response.read(64 * 1024):
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as error:  # return a useful upstream failure to Claude
            if not self.wfile.closed:
                message = json.dumps({"type": "error", "error": {"type": "proxy_error", "message": str(error)}}).encode()
                try:
                    self.send_response(502)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(message)))
                    self.end_headers()
                    self.wfile.write(message)
                except (BrokenPipeError, ConnectionResetError):
                    pass
        finally:
            connection.close()
            self.close_connection = True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4748)
    parser.add_argument("--upstream", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    upstream = urlsplit(args.upstream)
    if upstream.scheme != "http" or not upstream.hostname:
        raise SystemExit("--upstream must be an http:// URL")
    ProxyHandler.upstream_host = upstream.hostname
    ProxyHandler.upstream_port = upstream.port or 80
    server = ThreadingHTTPServer((args.listen, args.port), ProxyHandler)
    print(
        f"claude-vision proxy listening on http://{args.listen}:{args.port}; upstream={args.upstream}",
        file=sys.stderr,
        flush=True,
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
