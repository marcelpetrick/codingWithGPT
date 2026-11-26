# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the Linux source archive and its release metadata."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSE = "GPL-3.0-or-later"
SEMVER = re.compile(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
CONVENTIONAL_COMMIT = re.compile(r"^[a-z]+(?:\([^)]*\))?!?: .+")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, encoding="utf-8").strip()


def build_release(tag, output):
    if not SEMVER.fullmatch(tag):
        raise ValueError("Use a release tag such as v1.2.3")
    name = f"cleware-traffic-light-{tag}-linux"
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{name}.tar.gz"
    files = [
        "traffic_light.py",
        "agent_status.py",
        "requirements-monitor.txt",
        "README.md",
        "LICENSE",
    ]
    files.extend(
        filter(None, git("ls-files", "-z", "--", "docs/", "udev/").split("\0"))
    )
    with tarfile.open(archive, "w:gz") as bundle:
        for filename in files:
            bundle.add(ROOT / filename, arcname=f"{name}/{filename}", recursive=False)

    history = "HEAD"
    for candidate in git(
        "tag", "--merged", "HEAD", "--sort=-version:refname"
    ).splitlines():
        if candidate != tag and SEMVER.fullmatch(candidate):
            history = f"{candidate}..HEAD"
            break
    changes = git("log", "--format=%s", history, "--", ".").splitlines()
    bullets = [
        f"- {subject}" for subject in changes if CONVENTIONAL_COMMIT.fullmatch(subject)
    ]
    heading = f"# Changes in {tag}"
    (output / "CHANGELOG.md").write_text(
        "\n".join([heading, "", *bullets, ""]), encoding="utf-8"
    )

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": name,
        "documentNamespace": f"urn:uuid:{uuid.uuid4()}",
        "creationInfo": {
            "created": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "creators": ["Tool: cleware-traffic-light-release"],
        },
        "documentDescribes": ["SPDXRef-Package"],
        "packages": [
            {
                "SPDXID": "SPDXRef-Package",
                "name": name,
                "versionInfo": tag.removeprefix("v"),
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseDeclared": LICENSE,
                "licenseConcluded": LICENSE,
                "copyrightText": "NOASSERTION",
                "checksums": [{"algorithm": "SHA256", "checksumValue": digest}],
            },
            {
                "SPDXID": "SPDXRef-Websockets",
                "name": "websockets",
                "versionInfo": (ROOT / "requirements-monitor.txt")
                .read_text(encoding="utf-8")
                .strip()
                .split("==")[1],
                "downloadLocation": "https://pypi.org/project/websockets/",
                "filesAnalyzed": False,
                "licenseDeclared": "BSD-3-Clause",
                "licenseConcluded": "BSD-3-Clause",
                "copyrightText": "NOASSERTION",
            },
        ],
        "relationships": [
            {
                "spdxElementId": "SPDXRef-Websockets",
                "relationshipType": "OPTIONAL_DEPENDENCY_OF",
                "relatedSpdxElement": "SPDXRef-Package",
            }
        ],
    }
    (output / "sbom.spdx.json").write_text(
        json.dumps(sbom, indent=2) + "\n", encoding="utf-8"
    )
    artifacts = (archive, output / "sbom.spdx.json", output / "CHANGELOG.md")
    checksums = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in artifacts
    ]
    (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    return archive


def smoke_test(archive):
    with tempfile.TemporaryDirectory() as temporary:
        with tarfile.open(archive) as bundle:
            bundle.extractall(temporary, filter="data")
        script = (
            Path(temporary) / archive.name.removesuffix(".tar.gz") / "traffic_light.py"
        )
        subprocess.run(
            [sys.executable, script.with_name("agent_status.py"), "--help"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        result = subprocess.run(
            [
                sys.executable,
                script,
                "--usb-serial",
                "acceptance-fixture-missing",
                "cycle",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if (
            result.returncode != 1
            or "No matching Cleware USB-Ampel found" not in result.stderr
        ):
            sys.exit(f"Packaged command failed the missing-device check: {result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--output", default=ROOT / "dist", type=Path)
    args = parser.parse_args()
    smoke_test(build_release(args.tag, args.output))
