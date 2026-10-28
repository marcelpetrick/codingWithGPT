# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The workflow state machine (§8.1, §8.2, §16). Qt-free, so every rule is unit-tested.

Every Capture & Draft gets a new sequence id and cancel token. Results carry their sequence id; a
result for an older sequence is dropped, so a slow answer can never overwrite newer work.
"""

from dataclasses import dataclass
from enum import StrEnum

from linkedin_reply_assistant.cancel import CancelToken
from linkedin_reply_assistant.capture.frame import Capture
from linkedin_reply_assistant.extraction.base import ExtractionResult
from linkedin_reply_assistant.reply_engine.generator import Draft


class State(StrEnum):
    NO_SOURCE = "No source"
    SOURCE_READY = "Ready"
    CAPTURING = "Capturing"
    EXTRACTING = "Reading text"
    EXTRACTION_REVIEW = "Extraction needs review"
    GENERATING = "Generating"
    DRAFT_READY = "Draft ready"
    DRAFT_EDITED = "Draft edited"
    DRAFT_STALE = "Draft stale"
    INSERTING = "Inserting"
    INSERTED = "Inserted (not sent)"
    ERROR = "Error"


BUSY = {State.CAPTURING, State.EXTRACTING, State.GENERATING, State.INSERTING}


class WorkflowError(Exception):
    """An action is not allowed in the current state."""


@dataclass
class Workflow:
    state: State = State.NO_SOURCE
    sequence: int = 0
    active: int | None = None
    token: CancelToken | None = None
    capture: Capture | None = None
    extraction: ExtractionResult | None = None
    extracted_text: str = ""
    draft: Draft | None = None
    draft_text: str = ""
    error: str = ""
    stale_reason: str = ""

    # --- source ------------------------------------------------------------------------------

    def source_selected(self) -> None:
        if self.state == State.NO_SOURCE:
            self.state = State.SOURCE_READY

    def source_lost(self, message: str) -> None:
        self.cancel()
        self.state = State.NO_SOURCE
        self.error = message

    # --- Capture & Draft ---------------------------------------------------------------------

    @property
    def busy(self) -> bool:
        return self.state in BUSY

    def begin_capture(self) -> tuple[int, CancelToken]:
        """Start a new request. A running request is cancelled and superseded."""
        if self.state == State.NO_SOURCE:
            raise WorkflowError("Select the browser window first.")
        if self.state == State.INSERTING:
            raise WorkflowError("Wait until the insertion is finished.")
        if self.token is not None:
            self.token.cancel()
        self.sequence += 1
        self.active = self.sequence
        self.token = CancelToken()
        self.capture = None
        self.extraction = None
        self.extracted_text = ""
        self.draft = None  # a new capture invalidates the previous draft
        self.draft_text = ""
        self.error = self.stale_reason = ""
        self.state = State.CAPTURING
        return self.sequence, self.token

    def begin_regenerate(self) -> tuple[int, CancelToken]:
        """Regenerate from the (possibly edited) extracted text, without a new capture."""
        if not self.extracted_text.strip():
            raise WorkflowError("There is no extracted text to answer.")
        if self.state == State.INSERTING:
            raise WorkflowError("Wait until the insertion is finished.")
        if self.token is not None:
            self.token.cancel()
        self.sequence += 1
        self.active = self.sequence
        self.token = CancelToken()
        self.error = self.stale_reason = ""
        self.state = State.GENERATING
        return self.sequence, self.token

    def _current(self, seq: int) -> bool:
        return seq == self.active

    def captured(self, seq: int, capture: Capture) -> bool:
        if not self._current(seq):
            return False
        self.capture = capture
        self.state = State.EXTRACTING
        return True

    def extracted(self, seq: int, result: ExtractionResult, usable: bool) -> bool:
        if not self._current(seq):
            return False
        self.extraction = result
        self.extracted_text = result.raw_text
        self.state = State.GENERATING if usable else State.EXTRACTION_REVIEW
        if not usable:
            self._finish()
        return True

    def drafted(self, seq: int, draft: Draft) -> bool:
        if not self._current(seq):
            return False
        self.draft = draft
        self.draft_text = draft.reply
        self.state = State.DRAFT_READY
        self._finish()
        return True

    def failed(self, seq: int, message: str) -> bool:
        """Errors keep capture, extracted text and the last draft (§2.5, §21.5)."""
        if not self._current(seq):
            return False
        self.error = message
        self.state = State.ERROR
        self._finish()
        return True

    def cancel(self) -> None:
        if self.token is not None:
            self.token.cancel()
        self._finish()
        if self.state in BUSY - {State.INSERTING}:
            self.state = self._resting_state()

    def _finish(self) -> None:
        self.active = None
        self.token = None

    def _resting_state(self) -> State:
        if self.draft is not None:
            return State.DRAFT_STALE if self.stale_reason else State.DRAFT_READY
        if self.extracted_text:
            return State.EXTRACTION_REVIEW
        return State.SOURCE_READY

    # --- editing ------------------------------------------------------------------------------

    def edit_extracted_text(self, text: str) -> None:
        if text == self.extracted_text:
            return
        self.extracted_text = text
        if self.draft is not None and not self.busy:
            self.mark_stale("The extracted text changed. Regenerate the draft.")

    def edit_draft(self, text: str) -> None:
        if text == self.draft_text:
            return
        self.draft_text = text
        if self.state in (State.DRAFT_READY, State.INSERTED):
            self.state = State.DRAFT_EDITED

    def mark_stale(self, reason: str) -> None:
        if self.draft is not None:
            self.stale_reason = reason
            if not self.busy:
                self.state = State.DRAFT_STALE

    # --- insertion ---------------------------------------------------------------------------

    @property
    def can_insert(self) -> bool:
        return (
            self.state in (State.DRAFT_READY, State.DRAFT_EDITED, State.INSERTED, State.ERROR)
            and self.draft is not None
            and bool(self.draft_text.strip())
            and not self.stale_reason
        )

    def begin_insert(self) -> str:
        if not self.can_insert:
            raise WorkflowError("Insert needs a current, non-stale draft.")
        self.state = State.INSERTING
        return self.draft_text

    def inserted(self, ok: bool, message: str = "") -> None:
        """Inserted does not mean sent. A failed insertion keeps the draft (§21.7)."""
        if ok:
            self.state = State.INSERTED
            self.error = ""
        else:
            self.state = State.ERROR
            self.error = message
