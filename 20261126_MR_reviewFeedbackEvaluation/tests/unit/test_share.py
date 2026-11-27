# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for the share build (REQ-UI-9)."""

from mrreview.dataset import share_dataset


def _ds(text: str) -> dict[str, object]:
    return {
        "people": {
            "1": {"label": "Jade Crane", "name": "Real Name", "username": "rname", "kind": "human"}
        },
        "projects": [
            {"id": 5, "label": "Project Orion", "name": "fw", "path": "grp/fw", "web_url": "u"}
        ],
        "mrs": [{"url": "u", "title": text}],
        "threads": [{"url": "u", "path": "a/b.c", "excerpt": text}],
        "findings": [
            {"summary": text, "why": text, "ref": "https://git.example-corp.com/grp/fw/-/issues/7"}
        ],
        "meta": {},
    }


def test_share_scrubs_links_hosts_org_paths_and_mail() -> None:
    text = (
        "see https://git.example-corp.com/grp/fw/-/jobs/1, git://git@git.example-corp.com/grp/fw.git, "
        "log /builds/grp/fw/x.c, layer meta-example-corp-extras, example_corp, Example Corp, "
        "mail a.b@example-corp.com"
    )
    ds = share_dataset(_ds(text), "https://git.example-corp.com")
    out = ds["threads"][0]["excerpt"]
    for leak in ("example", "grp/fw", "a.b@", "http", "git://"):
        assert leak not in out.lower(), leak
    assert "Project Orion" in out
    assert "<org>" in out
    assert ds["findings"][0]["ref"] == "<link>"
    assert ds["people"]["1"]["name"] == "Jade Crane"
    assert ds["projects"][0]["path"] == "Project Orion"
    assert ds["meta"]["share"] is True
