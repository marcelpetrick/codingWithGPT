# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

import shutil
from pathlib import Path

from conftest import BERLIN, NOW, FakeHome
from test_procscan import make_process
from tokenusage2.config import Config
from tokenusage2.live import REDISCOVER_SECONDS, LiveSource
from tokenusage2.store import Store


def test_live_source_rediscovers_and_tracks_running_and_archived_homes(
    home: FakeHome, tmp_path: Path
) -> None:
    moment = [NOW]
    proc = tmp_path / "proc"
    source = LiveSource(
        Store(None), home.root, home.env, Config(), BERLIN, proc, clock=lambda: moment[0]
    )
    try:
        source.scan()
        assert {"claude", "codex", "codex-work"} <= {a.label for a in source.accounts()}
        assert source.generation() > 0
        assert source.quotas()
        assert "ACCOUNTS" in source.sources()

        (home.root / ".codex-new" / "sessions").mkdir(parents=True)
        make_process(proc, 321, "codex", ["codex"], {"CODEX_HOME": str(home.root / ".codex-new")})
        moment[0] += REDISCOVER_SECONDS
        source.scan()
        assert "codex-new" in {account.label for account in source.accounts()}
        assert source.running() == {"codex:~/.codex-new": 1}

        shutil.rmtree(home.root / ".codex-work")
        source.rediscover()
        assert "codex:~/.codex-work" in source.archived()
        assert "ARCHIVED (no longer on disk, history kept)" in source.sources()
    finally:
        source.close()
