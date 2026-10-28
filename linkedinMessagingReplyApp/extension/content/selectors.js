// Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
// All LinkedIn DOM knowledge lives here (VISION §29.5). Prefer semantic clues over class names.
"use strict";

globalThis.LRA_SELECTORS = {
  // The message composer: an editable text box inside the message form.
  composer: [
    "form[class*='msg-form'] [contenteditable='true'][role='textbox']",
    "[class*='msg-form__contenteditable'][contenteditable='true']",
    "[contenteditable='true'][role='textbox'][aria-label*='message' i]",
  ],
  // The title of the open conversation (participant name).
  threadTitle: [
    "[class*='msg-entity-lockup__entity-title']",
    "[class*='msg-thread__link-to-profile'] h2",
    "h2[class*='msg-overlay-bubble-header__title']",
  ],
};
