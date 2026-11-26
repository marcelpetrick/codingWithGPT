# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for configuration loading (REQ-LLM-1, REQ-SEC-1)."""

from datetime import date
from pathlib import Path

import pytest

from mrreview.config import Config, ConfigError, load_config


def test_defaults() -> None:
    cfg = load_config(None, env={})
    assert cfg.window_months == 12
    assert cfg.timezone == "Europe/Berlin"
    assert cfg.ollama_url == "http://192.168.100.67:11434"
    assert cfg.business_start_hour == 8
    assert cfg.business_end_hour == 18


def test_toml_and_env_override(tmp_path: Path) -> None:
    p = tmp_path / "c.toml"
    p.write_text(
        'gitlab_url = "https://gitlab.example/"\nwindow_months = 6\n'
        'holidays = ["2026-12-25"]\n[ollama_options]\ntemperature = 0.1\n',
        encoding="utf-8",
    )
    env = {"MRREVIEW_GITLAB_TOKEN": "glpat-x", "MRREVIEW_OLLAMA_MODEL": "m:1", "MRREVIEW_DB": "x.db"}
    cfg = load_config(p, env=env)
    assert cfg.gitlab_url == "https://gitlab.example"
    assert cfg.window_months == 6
    assert cfg.gitlab_token == "glpat-x"
    assert cfg.ollama_model == "m:1"
    assert cfg.db_path == Path("x.db")
    assert cfg.holidays == (date(2026, 12, 25),)
    assert cfg.ollama_options == {"temperature": 0.1}


def test_token_in_file_is_refused(tmp_path: Path) -> None:
    p = tmp_path / "c.toml"
    p.write_text('gitlab_token = "secret"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="environment"):
        load_config(p, env={})


def test_unknown_key_is_refused(tmp_path: Path) -> None:
    p = tmp_path / "c.toml"
    p.write_text('gitlab_urll = "x"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="unknown"):
        load_config(p, env={})


def test_repr_hides_token() -> None:
    cfg = Config(gitlab_token="glpat-secret")
    assert "glpat-secret" not in repr(cfg)


@pytest.mark.parametrize(
    ("text", "msg"),
    [
        ("window_months = 0\n", "window_months"),
        ('timezone = "Mars/Base"\n', "timezone"),
        ("ollama_concurrency = 0\n", "concurrency"),
        ("business_start_hour = 19\n", "business"),
        ('holidays = ["tomorrow"]\n', "holidays"),
        ("window_months = \"x\"\n", "window_months"),
    ],
)
def test_invalid_values(tmp_path: Path, text: str, msg: str) -> None:
    p = tmp_path / "c.toml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError, match=msg):
        load_config(p, env={})
