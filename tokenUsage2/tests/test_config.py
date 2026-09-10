# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

import pytest

from tokenusage2.config import Config, ConfigError, default_config_path, expand, load_config


def test_missing_default_file_is_an_empty_config(tmp_path: Path) -> None:
    assert load_config(None, tmp_path, {}) == Config()


def test_explicit_missing_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.toml", tmp_path, {})


def test_default_path_honours_xdg(tmp_path: Path) -> None:
    assert default_config_path(tmp_path, {}) == tmp_path / ".config/tokenusage2/config.toml"
    assert default_config_path(tmp_path, {"XDG_CONFIG_HOME": "/x"}) == Path(
        "/x/tokenusage2/config.toml"
    )


def test_full_file_is_parsed_and_expanded(tmp_path: Path) -> None:
    target = tmp_path / ".config" / "tokenusage2" / "config.toml"
    target.parent.mkdir(parents=True)
    target.write_text("""
[discovery]
claude_homes = ["~/work/.claude-client"]
codex_homes = ["$DATA/codex"]
opencode_dbs = []
ignore = ["~/.codex-old"]
scan_home = false
rc_files = ["~/.zshrc.local"]

[labels]
"~/.codex" = "private"

[backends]
"qwen*" = "gpu-box"
""")
    config = load_config(None, tmp_path, {"DATA": "/data"})
    assert config.claude_homes == (tmp_path / "work/.claude-client",)
    assert config.codex_homes == (Path("/data/codex"),)
    assert config.ignore == (tmp_path / ".codex-old",)
    assert config.scan_home is False
    assert config.rc_files == (tmp_path / ".zshrc.local",)
    assert config.labels == {str(tmp_path / ".codex"): "private"}
    assert config.backends == {"qwen*": "gpu-box"}
    assert config.source == target


@pytest.mark.parametrize(
    "content",
    [
        "discovery = 3",
        "[discovery]\nclaude_homes = 'x'",
        "[discovery]\nscan_home = 'yes'",
        "[labels]\nx = 1",
        "not toml [",
    ],
)
def test_invalid_files_raise(tmp_path: Path, content: str) -> None:
    path = tmp_path / "config.toml"
    path.write_text(content)
    with pytest.raises(ConfigError):
        load_config(path, tmp_path, {})


def test_expand() -> None:
    home = Path("/h")
    assert expand("~", home, {}) == home
    assert expand("~/a", home, {}) == Path("/h/a")
    assert expand("${HOME}/c", home, {"HOME": "/ignored"}) == Path("/h/c")
    assert expand("$X/b", home, {"X": "/x"}) == Path("/x/b")
    assert expand("$NOPE/b", home, {}) == Path("$NOPE/b")
