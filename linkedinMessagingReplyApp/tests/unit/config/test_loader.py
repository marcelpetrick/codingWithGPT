# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
from typing import Any

import pytest
import yaml

from linkedin_reply_assistant.config import loader
from linkedin_reply_assistant.config.loader import CATEGORIES, ConfigError, load_config


def defaults(name: str) -> dict[str, Any]:
    text = (Path(loader.__file__).parent.parent / "defaults" / name).read_text()
    data = yaml.safe_load(text)
    assert isinstance(data, dict)
    return data


def test_shipped_defaults_load(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert config.app.extraction.mode == "ocr"
    assert config.backends.backends[0].name == "network-ollama"
    assert config.backends.backends[0].scheme == "http"
    assert set(config.reply_rules.categories) == set(CATEGORIES)
    assert "sales_decline.md" in config.prompts
    assert "system.md" in config.prompts
    assert config.user_profile.allowed_facts


def test_user_file_overrides_default(tmp_path: Path) -> None:
    data = defaults("backends.yaml")
    data["backends"] = [data["backends"][1]]
    (tmp_path / "backends.yaml").write_text(yaml.safe_dump(data))
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "sales_decline.md").write_text("custom decline")
    config = load_config(tmp_path)
    assert [b.name for b in config.backends.backends] == ["local-ollama"]
    assert config.prompts["sales_decline.md"] == "custom decline"


def test_backends_sorted_by_priority() -> None:
    data = defaults("backends.yaml")
    data["backends"][0]["priority"] = 99
    parsed = loader.parse_backends(data)
    assert [b.name for b in parsed.backends] == ["local-ollama", "network-ollama"]


def test_user_config_dir_follows_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert loader.user_config_dir() == tmp_path / "linkedin-reply-assistant"
    monkeypatch.delenv("XDG_CONFIG_HOME")
    assert loader.user_config_dir() == Path.home() / ".config" / "linkedin-reply-assistant"


def test_load_config_defaults_to_user_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert load_config().app.language.policy == "mirror"


def test_invalid_yaml(tmp_path: Path) -> None:
    (tmp_path / "app.yaml").write_text("ui: [unclosed")
    with pytest.raises(ConfigError, match="invalid YAML"):
        load_config(tmp_path)


def test_top_level_must_be_mapping(tmp_path: Path) -> None:
    (tmp_path / "app.yaml").write_text("- a\n- b\n")
    with pytest.raises(ConfigError, match="top level"):
        load_config(tmp_path)


def test_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(loader, "_defaults_dir", lambda: tmp_path / "nowhere")
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path)


def mutate(name: str, path: list[str | int], value: Any) -> dict[str, Any]:
    data = defaults(name)
    target: Any = data
    for key in path[:-1]:
        target = target[key]
    if value is KeyError:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return data


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (["ui"], KeyError, "missing key 'ui'"),
        (["ui", "always_on_top"], "yes", "must be bool"),
        (["extraction", "mode"], "magic", "mode must be one of"),
        (["extraction", "min_characters"], True, "must be int"),
        (["language", "policy"], "random", "policy must be"),
        (["language", "supported"], [1, 2], "list of strings"),
    ],
)
def test_app_validation(path: list[str | int], value: Any, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        loader.parse_app(mutate("app.yaml", path, value))


def test_app_accepts_int_for_float() -> None:
    parsed = loader.parse_app(mutate("app.yaml", ["extraction", "min_confidence"], 70))
    assert parsed.extraction.min_confidence == 70.0


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (["backends", 0], "text", "must be a mapping"),
        (["backends", 0, "url"], "ftp://x", "url must start"),
        (["backends", 1, "name"], "network-ollama", "unique"),
        (["backends", 0, "priority"], "high", "must be int"),
        (["backends", 0, "model_preferences"], "x", "must be dict"),
    ],
)
def test_backends_validation(path: list[str | int], value: Any, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        loader.parse_backends(mutate("backends.yaml", path, value))


def test_backend_without_models_and_label() -> None:
    data = mutate("backends.yaml", ["backends", 0, "model_preferences"], KeyError)
    del data["backends"][0]["label"]
    parsed = loader.parse_backends(data)
    network = parsed.backends[0]
    assert network.reply_models == () and network.vision_models == ()
    assert network.label == "network-ollama"


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (["categories", "made_up"], {"policy": "x", "prompt": "y", "max_words": 1}, "unknown"),
        (["categories", "recruiting"], KeyError, "missing categories"),
        (["categories", "recruiting"], "text", "must be a mapping"),
        (["rules", 0], "text", "must be a mapping"),
        (["rules", 0, "category"], "nonsense", "unknown category"),
        (["rules", 0, "min_hits"], 0, "min_hits"),
        (["rules", 0, "min_hits"], 99, "min_hits"),
    ],
)
def test_reply_rules_validation(path: list[str | int], value: Any, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        loader.parse_reply_rules(mutate("reply_rules.yaml", path, value))


def test_user_profile_validation() -> None:
    with pytest.raises(ConfigError, match="name"):
        loader.parse_user_profile(mutate("user_profile.yaml", ["name"], KeyError))
