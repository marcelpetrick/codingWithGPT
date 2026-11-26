# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fixtures with a fake GitLab over real HTTP."""

from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from mrreview.config import Config
from mrreview.demo.fake_gitlab import FakeGitLab, serve
from mrreview.demo.fixture import Fixture, build_fixture
from mrreview.gitlab import GitLabClient
from mrreview.http import UrllibTransport


@dataclass
class Env:
    fake: FakeGitLab
    url: str
    client: GitLabClient
    cfg: Config
    fixture: Fixture


@pytest.fixture(scope="session")
def fixture_data() -> Fixture:
    return build_fixture(seed=7)


@pytest.fixture
def gl(fixture_data: Fixture) -> Iterator[Env]:
    fake = FakeGitLab(build_fixture(seed=7), token="tok-123")
    with serve(fake) as url:
        cfg = Config(gitlab_url=url, gitlab_token="tok-123", backoff_base_s=0.0, per_page=20)
        client = GitLabClient(
            url,
            "tok-123",
            UrllibTransport(),
            per_page=20,
            backoff_base=0.0,
            max_retries=3,
            sleep=lambda _s: None,
        )
        yield Env(fake, url, client, cfg, fake.fixture)
