# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from linkedin_reply_assistant.cancel import Cancelled, CancelToken


def test_cancel_token() -> None:
    token = CancelToken()
    assert not token.cancelled
    token.raise_if_cancelled()
    token.cancel()
    assert token.cancelled
    with pytest.raises(Cancelled):
        token.raise_if_cancelled()
