# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Direct Ollama HTTP API client with explicit timeouts, cancellation and model discovery."""

import base64
import json

import httpx

from linkedin_reply_assistant.backends.base import BackendError, ChatRequest, Health
from linkedin_reply_assistant.cancel import CancelToken
from linkedin_reply_assistant.config.loader import BackendConfig


class OllamaBackend:
    def __init__(self, config: BackendConfig, transport: httpx.BaseTransport | None = None) -> None:
        self.config = config
        timeout = httpx.Timeout(
            config.request_timeout_s, connect=config.connect_timeout_ms / 1000, pool=1.0
        )
        self._client = httpx.Client(base_url=config.url, timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def health(self) -> Health:
        """Probe reachability, version and installed models. Never raises."""
        probe = httpx.Timeout(self.config.connect_timeout_ms / 1000 * 3)
        try:
            version = self._client.get("/api/version", timeout=probe)
            version.raise_for_status()
            tags = self._client.get("/api/tags", timeout=probe)
            tags.raise_for_status()
            models = tuple(m["name"] for m in tags.json().get("models", []))
            return Health(True, str(version.json().get("version", "?")), models)
        except httpx.TimeoutException:
            return Health(False, error=f"timeout after {self.config.connect_timeout_ms} ms")
        except httpx.HTTPError as exc:
            return Health(False, error=f"unreachable: {type(exc).__name__}")
        except ValueError, KeyError, TypeError:
            return Health(False, error="invalid answer from endpoint")

    def chat(self, model: str, request: ChatRequest, cancel: CancelToken) -> str:
        """Stream a chat answer and return the full text. Cancellation closes the stream."""
        user: dict[str, object] = {"role": "user", "content": request.user}
        if request.images:
            user["images"] = [base64.b64encode(image).decode("ascii") for image in request.images]
        body: dict[str, object] = {
            "model": model,
            "messages": [{"role": "system", "content": request.system}, user],
            "stream": True,
            "think": False,
            "options": {"temperature": request.temperature},
        }
        if request.json_output:
            body["format"] = "json"
        parts: list[str] = []
        try:
            with self._client.stream("POST", "/api/chat", json=body) as response:
                if response.status_code != 200:
                    response.read()
                    raise BackendError(f"HTTP {response.status_code}: {response.text[:200]}")
                for line in response.iter_lines():
                    cancel.raise_if_cancelled()
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if "error" in chunk:
                        raise BackendError(str(chunk["error"]))
                    parts.append(chunk.get("message", {}).get("content", ""))
                    if chunk.get("done"):
                        break
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise BackendError(f"unreachable: {type(exc).__name__}", reachable=False) from exc
        except httpx.TimeoutException as exc:
            raise BackendError("generation timeout") from exc
        except httpx.HTTPError as exc:
            raise BackendError(f"transport error: {type(exc).__name__}", reachable=False) from exc
        except json.JSONDecodeError as exc:
            raise BackendError("invalid stream from endpoint") from exc
        text = "".join(parts).strip()
        if not text:
            raise BackendError("empty answer from model")
        return text
