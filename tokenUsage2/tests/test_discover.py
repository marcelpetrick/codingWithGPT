# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

from conftest import FakeHome
from tokenusage2.config import Config
from tokenusage2.discover import (
    BackendMap,
    backend_hints,
    backend_label,
    claude_identity,
    decode_jwt_claims,
    discover,
    rc_home_assignments,
)
from tokenusage2.model import Tool
from tokenusage2.procscan import AgentProcess


def test_every_home_is_found_without_hardcoding(home: FakeHome) -> None:
    found = discover(home.root, home.env, Config())
    accounts = {account.label: account for account in found.accounts}
    assert set(accounts) == {"claude", "codex", "codex-work", "codex-client", "opencode"}
    assert accounts["claude"].identity == "me@example.com"
    assert accounts["claude"].plan == "max"
    assert accounts["codex"].origin == "default"
    assert accounts["codex"].plan == "plus"
    assert accounts["codex-work"].origin == "rc:.zshrc"
    assert accounts["codex-work"].identity == "work@corp.example"
    assert accounts["codex-work"].plan == "team"
    assert accounts["codex-client"].identity == "API key"
    assert accounts["opencode"].tool is Tool.OPENCODE
    assert accounts["codex-work"].id == "codex:~/.codex-work"


def test_sibling_profiles_are_found_by_scanning_home(tmp_path: Path) -> None:
    (tmp_path / ".claude-work" / "projects").mkdir(parents=True)
    (tmp_path / ".config" / "codex-lab" / "sessions").mkdir(parents=True)
    (tmp_path / ".codex-empty").mkdir()
    found = discover(tmp_path, {}, Config())
    labels = {(a.label, a.origin) for a in found.accounts}
    assert labels == {("claude-work", "scan"), ("codex-lab-xdg", "scan")}
    assert discover(tmp_path, {}, Config(scan_home=False)).accounts == ()


def test_ignore_labels_and_notes(home: FakeHome) -> None:
    config = Config(
        ignore=(home.root / ".codex-work",),
        labels={str(home.root / ".codex"): "private"},
        claude_homes=(home.root / "missing",),
    )
    found = discover(home.root, home.env, config)
    labels = {account.label for account in found.accounts}
    assert "codex-work" not in labels
    assert "private" in labels
    assert any("ignored by config" in note for note in found.notes)
    assert any("without data (config)" in note for note in found.notes)


def test_environment_and_processes_add_homes(tmp_path: Path) -> None:
    (tmp_path / "elsewhere" / "sessions").mkdir(parents=True)
    (tmp_path / "live" / "projects").mkdir(parents=True)
    env = {"CODEX_HOME": str(tmp_path / "elsewhere")}
    process = AgentProcess(42, Tool.CLAUDE, {"CLAUDE_CONFIG_DIR": str(tmp_path / "live")})
    found = discover(tmp_path, env, Config(), [process])
    origins = {account.label: account.origin for account in found.accounts}
    assert origins == {"elsewhere": "env", "live": "process 42"}


def test_duplicate_labels_get_suffixes(tmp_path: Path) -> None:
    (tmp_path / "a" / ".claude" / "projects").mkdir(parents=True)
    (tmp_path / ".claude" / "projects").mkdir(parents=True)
    found = discover(tmp_path, {}, Config(claude_homes=(tmp_path / "a" / ".claude",)))
    assert [account.label for account in found.accounts] == ["claude", "claude-2"]


def test_backend_hints_resolve_locals_and_drop_credentials(home: FakeHome) -> None:
    hints = {
        hint.launcher: hint
        for hint in backend_hints({home.root / ".zshrc": (home.root / ".zshrc").read_text()})
    }
    gpu = hints["claude-gpu"]
    assert gpu.base_url == "http://10.0.0.5:11434"
    assert gpu.models == ("north-mini:q4",)
    assert gpu.label == "ollama@10.0.0.5"
    assert hints["claude-proxy"].label == "localhost:4747"
    assert hints["claude-proxy"].models == ("qwen/coder",)
    found = discover(home.root, home.env, Config())
    assert found.backends.hint("north-mini:q4") == "ollama@10.0.0.5"


def test_global_exports_and_unresolved_values(tmp_path: Path) -> None:
    text = "export ANTHROPIC_BASE_URL=https://gateway.example/v1\nexport ANTHROPIC_MODEL=m1\n"
    text += "broken() {\n  ANTHROPIC_BASE_URL=$UNSET\n}\n"
    hints = backend_hints({tmp_path / ".bashrc": text})
    assert [(h.launcher, h.label, h.models) for h in hints] == [
        ("(shell)", "gateway.example", ("m1",))
    ]


def test_rc_home_assignments(tmp_path: Path) -> None:
    text = (
        "set -gx CODEX_HOME ~/.codex-fish\n"
        'export CLAUDE_CONFIG_DIR="$HOME/.claude-x"\n'
        "# CODEX_HOME=/nope\n"
    )
    found = rc_home_assignments({tmp_path / "config.fish": text})
    assert found == [
        (Tool.CODEX, "~/.codex-fish", "config.fish"),
        (Tool.CLAUDE, "$HOME/.claude-x", "config.fish"),
    ]


def test_process_hints_come_first() -> None:
    process = AgentProcess(7, Tool.CLAUDE, {"ANTHROPIC_BASE_URL": "http://gpu:11434"}, "m1")
    found = discover(Path("/nonexistent"), {}, Config(), [process])
    assert found.hints[0].launcher == "pid 7"
    assert found.backends.hint("m1") == "ollama@gpu"


def test_backend_map_globs_override() -> None:
    backends = BackendMap({"qwen": "hinted"}, (("qw*", "configured"),))
    assert backends.override("qwen") == "configured"
    assert backends.override("other") is None
    assert backends.hint("qwen") == "hinted"


def test_backend_label() -> None:
    assert backend_label("http://h:11434") == "ollama@h"
    assert backend_label("https://api.example.com") == "api.example.com"
    assert backend_label("localhost:8080") == "localhost:8080"
    assert backend_label("http://h:99999") == "h"


def test_decode_jwt_claims_rejects_junk() -> None:
    assert decode_jwt_claims(None) == {}
    assert decode_jwt_claims("a.b") == {}
    assert decode_jwt_claims("a.!!!!.c") == {}
    assert decode_jwt_claims("a.WzFd.c") == {}


def test_claude_identity_variants(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / ".claude.json").write_text('{"primaryApiKey": "sk"}')
    assert claude_identity(profile, tmp_path) == ("API key", None)
    (profile / ".claude.json").write_text("[]")
    assert claude_identity(profile, tmp_path) == (None, None)
    (profile / ".claude.json").write_text(
        '{"oauthAccount": {"emailAddress": "a@b.c", "userRateLimitTier": "default_claude_max_20x"}}'
    )
    assert claude_identity(profile, tmp_path) == ("a@b.c", "max 20x")
