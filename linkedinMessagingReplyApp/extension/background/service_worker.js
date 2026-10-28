// Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
// Service worker: connects to the native host (lra-native-host) and forwards requests from the
// desktop app to the content script of the ACTIVE tab, only if that tab is LinkedIn messaging.
"use strict";

const HOST = "io.github.marcelpetrick.lra";
const MESSAGING = /^https:\/\/www\.linkedin\.com\/messaging\//;
let port = null;
let retryMs = 1000;

function reply(id, payload) {
  if (port) port.postMessage({ id, ...payload });
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  return tab;
}

function hello() {
  if (port) port.postMessage({ type: "hello", browser: navigator.userAgent.includes("Firefox") ? "firefox" : "chromium" });
}

async function handle(message) {
  if (message.type === "app_status") {
    if (message.connected) hello();  // the app may start after the browser
    return;
  }
  if (message.type === "error") return;
  const tab = await activeTab();
  if (!tab || !MESSAGING.test(tab.url || "")) {
    reply(message.id, { ok: false, error: "The active browser tab is not a LinkedIn conversation." });
    return;
  }
  try {
    const answer = await chrome.tabs.sendMessage(tab.id, { type: message.type, text: message.text, url: message.url });
    reply(message.id, answer || { ok: false, error: "no answer from the page" });
  } catch (error) {
    reply(message.id, { ok: false, error: "The LinkedIn page is not ready. Reload it once." });
  }
}

function connect() {
  port = chrome.runtime.connectNative(HOST);
  port.onMessage.addListener((message) => {
    retryMs = 1000;
    handle(message);
  });
  port.onDisconnect.addListener(() => {
    port = null;
    setTimeout(connect, retryMs);
    retryMs = Math.min(retryMs * 2, 60000);
  });
}

connect();
