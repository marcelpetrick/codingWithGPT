# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""End to end: app bridge -> native host -> extension -> fake LinkedIn page (§23.6).

Chromium runs with the real extension and the real native host. Every request is answered by a
Playwright route: LinkedIn URLs get a local fixture page, everything else is aborted and counted.
No byte goes to linkedin.com.
"""

import os
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, Page, Route, sync_playwright

from linkedin_reply_assistant.browser_bridge.inserter import CONVERSATION_CHANGED, Inserter
from linkedin_reply_assistant.browser_bridge.server import BridgeServer

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "tests" / "fixtures" / "pages"
THREAD = "https://www.linkedin.com/messaging/thread/2-abc/"
NO_COMPOSER = "https://www.linkedin.com/messaging/thread/2-empty/"
OTHER = "https://www.linkedin.com/feed/"


@dataclass
class Env:
    context: BrowserContext
    bridge: BridgeServer
    inserter: Inserter
    blocked: list[str]


def route(blocked: list[str]):  # type: ignore[no-untyped-def]
    def handler(route: Route) -> None:
        url = route.request.url
        if url.startswith(THREAD):
            route.fulfill(path=PAGES / "messaging_thread.html", content_type="text/html")
        elif url.startswith(NO_COMPOSER):
            route.fulfill(path=PAGES / "messaging_no_composer.html", content_type="text/html")
        elif url.startswith(OTHER):
            route.fulfill(body="<html><body>feed</body></html>", content_type="text/html")
        else:
            blocked.append(url)
            route.abort()

    return handler


@pytest.fixture(scope="module")
def env(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Env]:
    base = tmp_path_factory.mktemp("e2e")
    socket = base / "bridge.sock"
    profile = base / "profile"
    host = ROOT / ".venv" / "bin" / "lra-native-host"
    subprocess.run(
        [
            ROOT / "scripts" / "install_native_host.sh",
            str(host),
            "--target",
            str(profile / "NativeMessagingHosts"),
        ],
        check=True,
        capture_output=True,
    )
    bridge = BridgeServer(socket)
    bridge.start()
    blocked: list[str] = []
    extension = str(ROOT / "extension")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(profile),
            channel="chromium",
            headless=True,
            args=[f"--disable-extensions-except={extension}", f"--load-extension={extension}"],
            env={**os.environ, "LRA_BRIDGE_SOCKET": str(socket)},
        )
        context.route("**/*", route(blocked))
        deadline = time.monotonic() + 15
        while not bridge.connected and time.monotonic() < deadline:
            time.sleep(0.1)
        assert bridge.connected, "the extension did not connect through the native host"
        yield Env(context, bridge, Inserter(bridge), blocked)
        context.close()
    bridge.stop()


def open_page(env: Env, url: str) -> Page:
    for page in env.context.pages:
        if not page.url.startswith("chrome-extension://"):
            page.close()
    page = env.context.new_page()
    page.goto(url)
    page.bring_to_front()
    page.wait_for_function("() => document.readyState === 'complete'")
    time.sleep(0.3)  # content script runs at document_idle
    return page


def test_insert_into_composer_without_sending(env: Env) -> None:
    page = open_page(env, THREAD)
    draft = "Hi Anna, thank you!\n\nGreetings from Munich, Marcel"
    outcome = env.inserter.insert(draft, "Anna Keller")
    assert outcome.ok, outcome.message
    assert outcome.identity is not None and outcome.identity.thread_id == "2-abc"
    composer = page.inner_text("[role='textbox']")
    assert "Hi Anna, thank you!" in composer and "Greetings from Munich, Marcel" in composer
    assert page.evaluate("window.__sendClicks") == 0  # §23.6: no Send action
    assert page.evaluate("window.__submitted") is False
    assert page.evaluate("window.__keyEvents") == 0  # no synthetic keyboard input
    assert page.evaluate("window.__inputEvents") > 0  # the page framework saw the change
    assert env.bridge.browser == "chromium"


def test_ocr_noise_in_name_still_matches(env: Env) -> None:
    open_page(env, THREAD)
    assert env.inserter.insert("Hello", "Anna Kel1er").ok


def test_composer_not_empty_is_refused(env: Env) -> None:
    page = open_page(env, THREAD)
    page.fill("[role='textbox']", "my own text")
    outcome = env.inserter.insert("Hello", "Anna Keller")
    assert not outcome.ok and "not empty" in outcome.message
    assert page.inner_text("[role='textbox']") == "my own text"


def test_wrong_conversation_is_blocked(env: Env) -> None:
    page = open_page(env, THREAD)
    outcome = env.inserter.insert("Hello Tom", "Tom Brandt")
    assert not outcome.ok and outcome.message == CONVERSATION_CHANGED
    assert page.inner_text("[role='textbox']") == ""


def test_unknown_participant_needs_confirmation(env: Env) -> None:
    page = open_page(env, THREAD)
    first = env.inserter.insert("Hello", None)
    assert first.needs_confirmation and page.inner_text("[role='textbox']") == ""
    assert env.inserter.insert("Hello", None, confirmed=True).ok


def test_no_composer_is_refused(env: Env) -> None:
    open_page(env, NO_COMPOSER)
    outcome = env.inserter.insert("Hello", "Anna Keller")
    assert not outcome.ok and "composer not found" in outcome.message


def test_non_linkedin_tab_is_refused(env: Env) -> None:
    open_page(env, OTHER)
    outcome = env.inserter.insert("Hello", "Anna Keller")
    assert not outcome.ok and "not a LinkedIn conversation" in outcome.message


def test_no_request_left_the_machine(env: Env) -> None:
    assert not [url for url in env.blocked if "linkedin.com" in url]
