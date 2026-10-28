# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from PIL import Image

from linkedin_reply_assistant.backends.base import ChatResult
from linkedin_reply_assistant.capture.frame import Capture
from linkedin_reply_assistant.extraction.base import ExtractionResult
from linkedin_reply_assistant.reply_engine.classifier import Classification
from linkedin_reply_assistant.reply_engine.generator import Draft
from linkedin_reply_assistant.state.workflow import State, Workflow, WorkflowError

CAPTURE = Capture(1, Image.new("RGB", (4, 4)), "test", None)
RESULT = ExtractionResult("Anna 9:00\nHello there", (), "Anna", 0.9, "en", (), "ocr")
DRAFT = Draft(
    "Hi Anna",
    Classification("friendly_connection", 1, "", "friendly_reply", "model"),
    "en",
    False,
    (),
    ChatResult("x", "net", "net", "http://n", "m", 1.0),
)


def ready() -> Workflow:
    flow = Workflow()
    flow.source_selected()
    return flow


def drafted() -> Workflow:
    flow = ready()
    seq, _ = flow.begin_capture()
    flow.captured(seq, CAPTURE)
    flow.extracted(seq, RESULT, True)
    flow.drafted(seq, DRAFT)
    return flow


def test_happy_path() -> None:
    flow = ready()
    assert flow.state == State.SOURCE_READY
    seq, token = flow.begin_capture()
    assert flow.state == State.CAPTURING and flow.busy and not token.cancelled
    assert flow.captured(seq, CAPTURE) and flow.state == State.EXTRACTING
    assert flow.extracted(seq, RESULT, True) and flow.state == State.GENERATING
    assert flow.drafted(seq, DRAFT) and flow.state == State.DRAFT_READY
    assert flow.can_insert and flow.active is None
    assert flow.begin_insert() == "Hi Anna" and flow.state == State.INSERTING
    flow.inserted(True)
    assert flow.state == State.INSERTED and flow.state.value == "Inserted (not sent)"


def test_capture_needs_source() -> None:
    with pytest.raises(WorkflowError, match="Select the browser window"):
        Workflow().begin_capture()


def test_superseded_results_are_dropped() -> None:
    flow = ready()
    old_seq, old_token = flow.begin_capture()
    new_seq, _ = flow.begin_capture()
    assert old_token.cancelled
    assert not flow.captured(old_seq, CAPTURE)
    assert not flow.extracted(old_seq, RESULT, True)
    assert not flow.drafted(old_seq, DRAFT)
    assert not flow.failed(old_seq, "late error")
    assert flow.state == State.CAPTURING and flow.draft is None
    assert flow.captured(new_seq, CAPTURE)


def test_new_capture_invalidates_draft() -> None:
    flow = drafted()
    flow.begin_capture()
    assert flow.draft is None and not flow.can_insert


def test_unusable_extraction_stops_for_review() -> None:
    flow = ready()
    seq, _ = flow.begin_capture()
    flow.captured(seq, CAPTURE)
    flow.extracted(seq, RESULT, False)
    assert flow.state == State.EXTRACTION_REVIEW and flow.active is None
    assert flow.extracted_text == RESULT.raw_text


def test_cancel_returns_to_resting_state_and_drops_late_results() -> None:
    flow = ready()
    seq, token = flow.begin_capture()
    flow.cancel()
    assert token.cancelled and flow.state == State.SOURCE_READY
    assert not flow.captured(seq, CAPTURE)
    review = ready()
    seq, _ = review.begin_capture()
    review.captured(seq, CAPTURE)
    review.extracted(seq, RESULT, True)
    review.cancel()
    assert review.state == State.EXTRACTION_REVIEW
    kept = drafted()
    seq, _ = kept.begin_regenerate()
    kept.cancel()
    assert kept.state == State.DRAFT_READY
    kept.mark_stale("changed")
    seq, _ = kept.begin_regenerate()
    kept.cancel()
    assert kept.state == State.DRAFT_READY  # regenerate cleared the stale reason
    idle = drafted()
    idle.cancel()
    assert idle.state == State.DRAFT_READY


def test_errors_keep_state() -> None:
    flow = drafted()
    seq, _ = flow.begin_regenerate()
    assert flow.failed(seq, "All AI backends are unavailable")
    assert flow.state == State.ERROR and flow.extracted_text and flow.draft is DRAFT
    assert flow.can_insert  # the previous draft is still valid


def test_regenerate_requires_text_and_idle_insert() -> None:
    with pytest.raises(WorkflowError, match="no extracted text"):
        ready().begin_regenerate()
    flow = drafted()
    flow.begin_insert()
    with pytest.raises(WorkflowError, match="insertion"):
        flow.begin_regenerate()
    with pytest.raises(WorkflowError, match="insertion"):
        flow.begin_capture()


def test_editing_marks_stale_and_edited() -> None:
    flow = drafted()
    flow.edit_draft("Hi Anna")
    assert flow.state == State.DRAFT_READY
    flow.edit_draft("Hi Anna!")
    assert flow.state == State.DRAFT_EDITED and flow.can_insert
    flow.edit_extracted_text(RESULT.raw_text)
    assert flow.state == State.DRAFT_EDITED
    flow.edit_extracted_text("changed text")
    assert flow.state == State.DRAFT_STALE and not flow.can_insert
    with pytest.raises(WorkflowError):
        flow.begin_insert()


def test_conversation_change_marks_stale() -> None:
    flow = drafted()
    flow.mark_stale("Conversation changed — recapture required")
    assert flow.state == State.DRAFT_STALE and not flow.can_insert
    empty = ready()
    empty.mark_stale("x")
    assert empty.state == State.SOURCE_READY


def test_failed_insert_keeps_draft() -> None:
    flow = drafted()
    flow.begin_insert()
    flow.inserted(False, "LinkedIn composer not found")
    assert flow.state == State.ERROR and flow.draft_text == "Hi Anna" and flow.can_insert
    flow.inserted(True)
    flow.edit_draft("Hi Anna, again")
    assert flow.state == State.DRAFT_EDITED


def test_source_lost() -> None:
    flow = drafted()
    flow.source_lost("Browser capture source is unavailable.")
    assert flow.state == State.NO_SOURCE and flow.error
    flow.source_selected()
    assert flow.state == State.SOURCE_READY
    flow.source_selected()
    assert flow.state == State.SOURCE_READY


def test_edge_transitions() -> None:
    flow = drafted()
    _, first = flow.begin_regenerate()
    _, second = flow.begin_regenerate()  # supersedes the running regeneration
    assert first.cancelled and not second.cancelled
    flow.mark_stale("changed while busy")
    assert flow.state == State.GENERATING and flow.stale_reason
    flow.edit_extracted_text("edited while busy")
    assert flow.state == State.GENERATING
    no_draft = ready()
    no_draft.edit_extracted_text("text")
    assert no_draft.state == State.SOURCE_READY
    edited = drafted()
    edited.edit_draft("one")
    edited.edit_draft("two")
    assert edited.state == State.DRAFT_EDITED
