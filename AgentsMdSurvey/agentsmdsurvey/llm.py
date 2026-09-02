"""Layer 3b — optional semantic enrichment.

Everything here is optional and cached. The deterministic pipeline produces a
complete report without it; this pass adds what a lexicon cannot:

* **Discovery.** The directives the taxonomy never anticipated get embedded and
  clustered, and each cluster that spans several scopes is labelled. That is how
  a topic nobody thought to write a pattern for becomes visible.
* **Confirmation.** The polarity shortlist — the weakest deterministic signal —
  is put to the model as a yes/no question per pair, so the report can say which
  of those candidates are real disagreements.

Two rules keep this honest:

1. **The model may label, cluster and phrase. It never counts.** Every number in
   the report comes from the deterministic layers, including the counts attached
   to the labels invented here.
2. **Every call is cached on disk under the SHA-256 of its input.** A second run
   costs nothing and returns byte-identical output, so the report stays
   reproducible for somebody who has no model at all.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .stats import Finding, Survey
from .taxonomy import TOPIC_BY_ID

# Cosine similarity above which two directives are the same rule in different
# words. Deliberately strict: a loose threshold produces one enormous cluster
# labelled "software development".
SIMILARITY = 0.72

# A cluster is only worth labelling when independent scopes contributed to it.
MIN_CLUSTER_SCOPES = 2

LABEL_PROMPT = """You are helping to classify rules found in AI-agent instruction files.

Below are sentences that a clustering step grouped together. Give the group a
topic label: a noun phrase of two to five words, in the style of "Conventional
Commits" or "Never push without being asked". Answer with the label only, no
punctuation, no explanation.

Sentences:
{sentences}
"""

CONTRADICTION_PROMPT = """Two repositories state rules on the same topic: {topic}.

Repository A says:
{a}

Repository B says:
{b}

Do these two rules actually contradict each other, such that a single shared
instruction file could not contain both? Answer with exactly one word: YES or NO.
"""


Transport = Callable[[str, dict[str, Any]], dict[str, Any]]


def _http_transport(host: str) -> Transport:
    def call(path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{host.rstrip('/')}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))

    return call


@dataclass
class Cache:
    """Disk cache keyed by the hash of the request."""

    directory: Path

    def key(self, *parts: str) -> str:
        digest = hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()
        return digest

    def get(self, key: str) -> Any | None:
        path = self.directory / f"{key}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def put(self, key: str, value: Any) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / f"{key}.json").write_text(json.dumps(value), encoding="utf-8")


class Client:
    """Cached access to an Ollama-compatible endpoint."""

    def __init__(self, cache: Cache, transport: Transport, model: str, embed_model: str) -> None:
        self.cache = cache
        self.transport = transport
        self.model = model
        self.embed_model = embed_model
        self.calls = 0
        self.cache_hits = 0
        self.failures = 0

    def embed(self, text: str) -> list[float] | None:
        key = self.cache.key("embed", self.embed_model, text)
        cached = self.cache.get(key)
        if cached is not None:
            self.cache_hits += 1
            return cached
        try:
            response = self.transport("/api/embed", {"model": self.embed_model, "input": text})
        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
            self.failures += 1
            return None
        vectors = response.get("embeddings") or ([response["embedding"]] if "embedding" in response else [])
        if not vectors:
            self.failures += 1
            return None
        self.calls += 1
        self.cache.put(key, vectors[0])
        return vectors[0]

    def ask(self, prompt: str) -> str | None:
        key = self.cache.key("chat", self.model, prompt)
        cached = self.cache.get(key)
        if cached is not None:
            self.cache_hits += 1
            return cached
        try:
            response = self.transport(
                "/api/chat",
                {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0},
                },
            )
        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
            self.failures += 1
            return None
        content = (response.get("message") or {}).get("content", "").strip()
        if not content:
            self.failures += 1
            return None
        self.calls += 1
        self.cache.put(key, content)
        return content


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def cluster(items: list[tuple[str, list[float]]], threshold: float = SIMILARITY) -> dict[str, int]:
    """Greedy nearest-centroid clustering, deterministic in the given order.

    Chosen over anything cleverer because it has no random seed and no
    iteration count: the same input yields the same clusters forever, which is
    the point of caching in the first place.
    """
    centroids: list[list[float]] = []
    sizes: list[int] = []
    assignment: dict[str, int] = {}
    for key, vector in items:
        best_index, best_score = -1, threshold
        for index, centroid in enumerate(centroids):
            score = _cosine(vector, centroid)
            if score > best_score:
                best_index, best_score = index, score
        if best_index < 0:
            centroids.append(list(vector))
            sizes.append(1)
            assignment[key] = len(centroids) - 1
        else:
            size = sizes[best_index]
            centroids[best_index] = [
                (c * size + v) / (size + 1) for c, v in zip(centroids[best_index], vector)
            ]
            sizes[best_index] = size + 1
            assignment[key] = best_index
    return assignment


def enrich(
    survey: Survey,
    *,
    host: str = "http://localhost:11434",
    model: str = "qwen3.8:30b-a3b-q4_K_M",
    embed_model: str = "nomic-embed-text",
    cache_dir: Path = Path(".cache"),
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Cluster the unclassified tail, label it, and test the polarity shortlist."""
    client = Client(Cache(cache_dir), transport or _http_transport(host), model, embed_model)

    # --- discovery: what the lexicon never anticipated ----------------------
    unclassified: dict[str, dict[str, Any]] = {}
    for item, directive in survey.directives():
        if directive.topics:
            continue
        entry = unclassified.setdefault(
            directive.fingerprint,
            {"text": directive.text, "normalized": directive.normalized, "scopes": set(), "directives": []},
        )
        entry["scopes"].add(item.scope)
        entry["directives"].append(directive)

    vectors: list[tuple[str, list[float]]] = []
    for fingerprint in sorted(unclassified):
        vector = client.embed(unclassified[fingerprint]["normalized"])
        if vector is not None:
            vectors.append((fingerprint, vector))

    labelled: list[dict[str, Any]] = []
    if vectors:
        assignment = cluster(vectors)
        members: dict[int, list[str]] = {}
        for fingerprint, index in assignment.items():
            members.setdefault(index, []).append(fingerprint)

        for index, fingerprints in sorted(members.items()):
            scopes: set[str] = set()
            for fingerprint in fingerprints:
                scopes |= unclassified[fingerprint]["scopes"]
            if len(scopes) < MIN_CLUSTER_SCOPES:
                continue
            sample = sorted(unclassified[f]["normalized"] for f in fingerprints)[:12]
            label = client.ask(LABEL_PROMPT.format(sentences="\n".join(f"- {s}" for s in sample)))
            if not label:
                continue
            label = label.splitlines()[-1].strip().strip('"').strip(".")
            for fingerprint in fingerprints:
                for directive in unclassified[fingerprint]["directives"]:
                    directive.cluster = label
            labelled.append(
                {
                    "label": label,
                    "scopes": sorted(scopes),
                    "directives": sum(len(unclassified[f]["directives"]) for f in fingerprints),
                    "examples": sample[:3],
                }
            )

    labelled.sort(key=lambda row: (-len(row["scopes"]), -row["directives"], row["label"]))
    if labelled:
        survey.findings.append(
            Finding(
                id="discovered_topics",
                severity="insight",
                title=f"{len(labelled)} recurring themes the taxonomy did not anticipate",
                detail=(
                    "Found by embedding the directives the lexicon left unclassified and clustering "
                    "them, then asking the model only to name each cluster. The counts are still "
                    "deterministic — they are member and scope counts, not model output. A theme "
                    "here that keeps recurring is a candidate for a real taxonomy entry."
                ),
                evidence=[
                    f"{row['label']} — {len(row['scopes'])} scopes, {row['directives']} directives "
                    f"(e.g. \"{row['examples'][0][:90]}\")"
                    for row in labelled[:12]
                ],
            )
        )

    # --- confirmation: which polarity candidates are real -------------------
    shortlist = next((f for f in survey.findings if f.id == "contradictions"), None)
    confirmed: list[str] = []
    if shortlist is not None:
        for topic_id, pair in _polarity_pairs(survey)[:12]:
            topic = TOPIC_BY_ID[topic_id]
            answer = client.ask(
                CONTRADICTION_PROMPT.format(topic=topic.label, a=pair[0][1], b=pair[1][1])
            )
            if answer and answer.strip().upper().startswith("YES"):
                confirmed.append(f"{topic.label}: {pair[0][0]} vs {pair[1][0]}")
        if confirmed:
            survey.findings.append(
                Finding(
                    id="confirmed_contradictions",
                    severity="inconsistency",
                    title=f"{len(confirmed)} of the polarity candidates are real disagreements",
                    detail=(
                        "Each pair was put to the model as a yes/no question: could one shared "
                        "instruction file contain both rules? These are the ones it said no to — "
                        "decisions the canonical file has to make rather than inherit."
                    ),
                    evidence=confirmed,
                )
            )

    return {
        "model": model,
        "embed_model": embed_model,
        "calls": client.calls,
        "cache_hits": client.cache_hits,
        "failures": client.failures,
        "clusters": labelled,
        "confirmed_contradictions": confirmed,
    }


def _polarity_pairs(survey: Survey) -> list[tuple[str, tuple[tuple[str, str], tuple[str, str]]]]:
    """One representative positive and negative wording per split topic."""
    sides: dict[str, dict[bool, tuple[str, str]]] = {}
    for item, directive in survey.directives():
        if directive.hardness != "hard":
            continue
        for topic in directive.topics:
            bucket = sides.setdefault(topic, {})
            bucket.setdefault(directive.negative, (item.scope, directive.text))
    return [
        (topic, (bucket[False], bucket[True]))
        for topic, bucket in sorted(sides.items())
        if False in bucket and True in bucket
    ]
