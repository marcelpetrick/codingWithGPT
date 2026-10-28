// Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
// Content script on LinkedIn messaging pages. Two actions only (AGENTS.md, bent rule B2):
//   identify: report the thread title and URL of this page.
//   insert:   put an approved draft into an EMPTY composer, like a paste, and read it back.
// It never clicks, never creates key events, never submits, never navigates.
"use strict";

function firstMatch(selectors) {
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) return element;
  }
  return null;
}

function normalize(text) {
  return (text || "").replace(/\s+/g, " ").trim();
}

function identify() {
  const title = firstMatch(globalThis.LRA_SELECTORS.threadTitle);
  return { ok: true, title: normalize(title && title.textContent), url: location.href };
}

function insert(text, expectedUrl) {
  if (expectedUrl && expectedUrl !== location.href) {
    return { ok: false, error: "Conversation changed — recapture required." };
  }
  const composer = firstMatch(globalThis.LRA_SELECTORS.composer);
  if (!composer) {
    return { ok: false, error: "LinkedIn composer not found. Nothing was inserted." };
  }
  if (normalize(composer.innerText)) {
    return { ok: false, error: "The LinkedIn composer is not empty. Clear it first." };
  }
  composer.focus();
  const lines = text.split("\n");
  lines.forEach((line, index) => {
    if (index > 0) document.execCommand("insertParagraph");
    if (line) document.execCommand("insertText", false, line);
  });
  // Frameworks listen to input events; execCommand fires them, this one is a safety net.
  composer.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText" }));
  const readback = composer.innerText;
  return { ok: normalize(readback).includes(normalize(text)), readback };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "identify") sendResponse(identify());
  else if (message.type === "insert") sendResponse(insert(String(message.text || ""), message.url));
  else sendResponse({ ok: false, error: "unknown request" });
});
