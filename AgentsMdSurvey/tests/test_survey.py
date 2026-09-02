"""Tests for the layers that must never change silently.

Discovery and segmentation are the foundation every number rests on, so they
are pinned against fixtures. The semantic pass is exercised through an injected
transport, which also proves it works offline from cache.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentsmdsurvey import synth  # noqa: E402
from agentsmdsurvey.cli import build_survey  # noqa: E402
from agentsmdsurvey.discovery import discover, first_party, mark_duplicates  # noqa: E402
from agentsmdsurvey.llm import Cache, Client, cluster, enrich  # noqa: E402
from agentsmdsurvey.parse import normalize, parse  # noqa: E402
from agentsmdsurvey.redact import load_stems, mask, redact  # noqa: E402
from agentsmdsurvey.taxonomy import classify  # noqa: E402

ROOT_AGENTS = """# AGENTS.md

## Commits

- Use Conventional Commits: `feat(scope): summary`.
- One concern per commit; never mix a refactor with a feature.

## Quality gate

Run the gate before every commit. The pipeline must be green.

```bash
./gate.sh
```

## House habits

- Keep the kettle on while the render finishes.
"""

DOCS_AGENTS = """# Repository Guidelines

## Commits
- Use Conventional Commits: `feat(scope): summary`.

## Privacy Rules
- Never commit secrets or personal data.

## House habits
- Keep the kettle warm while the render finishes.
"""

CLAUDE_STUB = "# CLAUDE.md\n\nSee AGENTS.md.\n"


def build_tree(base: Path) -> None:
    """A miniature ~/repos: two projects, a vendored clone, a build copy."""
    alpha = base / "alpha"
    (alpha / ".git").mkdir(parents=True)
    (alpha / "AGENTS.md").write_text(ROOT_AGENTS)
    (alpha / "CLAUDE.md").write_text(CLAUDE_STUB)

    beta = base / "beta"
    (beta / "documents").mkdir(parents=True)
    (beta / ".git").mkdir()
    (beta / "documents" / "AGENTS.md").write_text(DOCS_AGENTS)
    (beta / "build" / "docs").mkdir(parents=True)
    (beta / "build" / "docs" / "AGENTS.md").write_text(DOCS_AGENTS)

    quiet = base / "quiet"
    (quiet / ".git").mkdir(parents=True)
    (quiet / "main.py").write_text("print('hi')\n")

    vendored = base / "alpha" / "vendor" / "someone-else"
    vendored.mkdir(parents=True)
    (vendored / "AGENTS.md").write_text("# Their rules\n\n- Do it their way.\n")

    # The same rules, adopted by a second project. Not a copy to discount:
    # both repositories genuinely carry them.
    gamma = base / "gamma"
    (gamma / ".git").mkdir(parents=True)
    (gamma / "AGENTS.md").write_text(DOCS_AGENTS)

    ignored = base / "beta" / "node_modules" / "pkg"
    ignored.mkdir(parents=True)
    (ignored / "AGENTS.md").write_text("# Package\n\n- Irrelevant.\n")


class DiscoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_tree(self.root)
        self.files, self.repos = discover(self.root, use_git=False)
        self.duplicates = mark_duplicates(self.files)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_pruned_directories_are_never_walked(self) -> None:
        self.assertFalse(any("node_modules" in f.rel_path for f in self.files))

    def test_vendored_files_are_excluded_from_first_party(self) -> None:
        vendored = [f for f in self.files if "vendor" in f.rel_path]
        self.assertEqual(len(vendored), 1)
        self.assertTrue(vendored[0].vendored)
        self.assertNotIn(vendored[0], first_party(self.files))

    def test_build_copy_is_marked_as_duplicate_not_source(self) -> None:
        self.assertEqual(len(self.duplicates), 1)
        survivors = [f.rel_path for f in first_party(self.files) if f.name == "AGENTS.md"]
        self.assertIn("beta/documents/AGENTS.md", survivors)
        self.assertNotIn("beta/build/docs/AGENTS.md", survivors)

    def test_docs_file_is_attributed_to_the_project_above_it(self) -> None:
        docs = next(f for f in self.files if f.rel_path == "beta/documents/AGENTS.md")
        self.assertEqual(docs.scope, "beta")
        self.assertEqual(docs.location, "docs")

    def test_a_copy_in_another_repository_still_counts(self) -> None:
        """Identical bytes in two repositories means two instructed projects."""
        twins = [f for f in self.files if f.rel_path in ("beta/documents/AGENTS.md", "gamma/AGENTS.md")]
        self.assertEqual(len(twins), 2)
        for twin in twins:
            self.assertFalse(twin.generated, f"{twin.rel_path} was wrongly discounted")
            self.assertIn(twin, first_party(self.files))

    def test_repository_without_instructions_is_still_seen(self) -> None:
        self.assertIn("quiet", [r.name for r in self.repos])

    def test_nested_checkouts_do_not_count_towards_coverage(self) -> None:
        for repo in self.repos:
            self.assertEqual(repo.surveyable, repo.depth == 1)


class ParseTest(unittest.TestCase):
    def test_normalization_collapses_markdown_decoration(self) -> None:
        self.assertEqual(
            normalize("- **Use** `Conventional Commits`, [see](http://x) here."),
            "use conventional commits, see here",
        )

    def test_code_fences_never_produce_directives(self) -> None:
        document = parse(ROOT_AGENTS)
        self.assertTrue(all("gate.sh" not in d.normalized for d in document.directives))
        self.assertGreater(document.code_lines, 0)

    def test_bullets_and_imperative_sentences_both_count(self) -> None:
        document = parse(ROOT_AGENTS)
        forms = {d.form for d in document.directives}
        self.assertIn("bullet", forms)
        self.assertIn("sentence", forms)

    def test_hardness_is_read_from_the_wording(self) -> None:
        document = parse(ROOT_AGENTS)
        never = next(d for d in document.directives if "never mix" in d.normalized)
        self.assertEqual(never.hardness, "hard")
        self.assertTrue(never.negative)

    def test_heading_path_is_tracked(self) -> None:
        document = parse(ROOT_AGENTS)
        commit_rule = next(d for d in document.directives if "conventional commits" in d.normalized)
        self.assertEqual(commit_rule.heading_path, ["AGENTS.md", "Commits"])

    def test_identical_wording_shares_a_fingerprint(self) -> None:
        a = parse(ROOT_AGENTS).directives
        b = parse(DOCS_AGENTS).directives
        shared = {d.fingerprint for d in a} & {d.fingerprint for d in b}
        self.assertTrue(shared, "the repeated conventional-commits line must match across files")


class TaxonomyTest(unittest.TestCase):
    def test_known_rules_land_on_the_expected_topic(self) -> None:
        cases = {
            "use conventional commits: feat(scope): summary": "commit.conventional",
            "never push to origin": "vcs.never_push",
            "pin every dependency to an exact version": "deps.exact_pins",
            "never commit secrets or api keys": "safety.secrets",
            "english is mandatory for all project-facing work": "lang.english_only",
        }
        for text, expected in cases.items():
            self.assertIn(expected, classify(text), text)

    def test_make_sure_is_not_a_toolchain_rule(self) -> None:
        self.assertNotIn("env.toolchain", classify("make sure the output is correct"))


class RedactionTest(unittest.TestCase):
    """Names that must not leave the machine, and words that only look like them.

    The stems here are invented. The real ones live in an untracked file, so
    this test file — which is public — never names a customer.
    """

    STEMS = ("acmeanalyzer", "zqt", "widget_app", "x742", "ecoil")

    def test_the_first_character_survives_and_the_length_is_honest(self) -> None:
        self.assertEqual(mask("acmeanalyzer"), "a" + "█" * 11)
        self.assertEqual(redact("acmeanalyzer", self.STEMS), "a███████████")

    def test_every_way_a_name_is_written_is_caught(self) -> None:
        for name in (
            "acmeanalyzer.wiki",
            "acmeAnalyzer",
            "acmeanalyzer-worktrees",
            "zqt",
            "zqt.wiki",
            "zqt_automatedqualitytest",
            "widget_app_demo",
            "X742_HMI",
            "x742_hmi_app",
            "meta-imx8mm-vendor-x742",
            "eCoil_BSP",
        ):
            masked = redact(name, self.STEMS)
            self.assertEqual(masked[0], name[0], name)
            self.assertEqual(len(masked), len(name), name)
            self.assertNotIn(name[1:].lower(), masked.lower(), f"{name} survived redaction")

    def test_a_path_is_masked_segment_by_segment(self) -> None:
        self.assertEqual(
            redact("zqt/submodules/acmeAnalyzer", self.STEMS), "z██/submodules/a███████████"
        )
        self.assertEqual(
            redact("eCoil_BSP/SKILLS/app/SKILL.md", self.STEMS), "e████████/SKILLS/app/SKILL.md"
        )

    def test_a_stem_inside_a_word_is_not_a_repository_name(self) -> None:
        """Masking keys on where the stem sits, which is the whole point.

        A stem that *starts* a name token is masked together with whatever
        follows it, because that is how a repository grows a suffix
        (name, name.wiki, name_tests). A stem buried inside a word is left
        alone — otherwise every occurrence of "prompt" would be redacted.
        """
        for text in ("azqtx marker", "the recoiled cable", "unxx742 units"):
            self.assertEqual(redact(text, ("zqt", "ecoil", "x742")), text)

        self.assertEqual(redact("zqt_tests", ("zqt",)), "z████████")
        self.assertEqual(redact("x7420", ("x742",)), "x████")

    def test_unrelated_repository_names_survive(self) -> None:
        for name in ("recognizer", "GarminActivityMap", "CuteLingoExpress"):
            self.assertEqual(redact(name, self.STEMS), name)

    def test_a_missing_stem_file_yields_no_stems_rather_than_an_error(self) -> None:
        self.assertEqual(load_stems(Path("/nonexistent/redact.stems")), ())

    def test_stem_file_ignores_comments_and_blank_lines(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "redact.stems"
            path.write_text("# a comment\n\nAlpha\n  beta  \n")
            self.assertEqual(load_stems(path), ("alpha", "beta"))


class PipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_tree(self.root)
        self.survey = build_survey(self.root, use_git=False)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_headline_counts_only_first_party_material(self) -> None:
        head = self.survey.headline()
        self.assertEqual(head["repos_scanned"], 4)
        self.assertEqual(head["repos_with_instructions"], 3)
        self.assertEqual(head["files_first_party"], 4)

    def test_coverage_separates_dormant_from_active_repositories(self) -> None:
        """A repository nobody commits to is not a gap worth reporting."""
        from datetime import date, timedelta

        from agentsmdsurvey.stats import Survey

        today = date.today().isoformat()
        recent = (date.today() - timedelta(days=10)).isoformat()
        old = (date.today() - timedelta(days=900)).isoformat()
        repos = self.survey.repos
        for repo in repos:
            # alpha is instructed and committed to *today* — zero days old, and
            # zero is falsy, which is exactly how it once got filed as dormant.
            # quiet is uninstructed and recent; everything else is long dormant.
            if repo.name == "alpha":
                repo.last_commit_date = today
            elif repo.name == "quiet":
                repo.last_commit_date = recent
            else:
                repo.last_commit_date = old

        rebuilt = Survey(
            self.survey.root, self.survey.files, repos, self.survey.parsed, self.survey.duplicate_groups
        )
        cov = rebuilt.coverage()
        self.assertEqual(cov["repos"], 4)
        self.assertEqual(cov["active_repos"], 2)
        self.assertEqual(cov["active_instructed"], 1)
        self.assertEqual(cov["dormant_repos"], 2)
        self.assertAlmostEqual(cov["active_share"], 0.5)
        self.assertEqual(cov["active_with_agents_md"], 1)

    def test_shared_rule_is_counted_once_per_scope(self) -> None:
        rows = {row["id"]: row for row in self.survey.topic_table()}
        self.assertEqual(rows["commit.conventional"]["scopes"], 3)

    def test_findings_include_the_duplicate_and_the_backlog(self) -> None:
        ids = {f.id for f in self.survey.findings}
        self.assertIn("duplicates", ids)
        self.assertIn("coverage", ids)

    def test_survey_json_round_trips(self) -> None:
        payload = json.loads(json.dumps(self.survey.to_dict()))
        self.assertEqual(payload["headline"]["scopes"], 3)

    def test_canonical_file_only_quotes_rules_above_the_threshold(self) -> None:
        document = synth.render(self.survey, min_scopes=2)
        self.assertIn("Conventional Commits", document)
        self.assertNotIn("One concern per commit", document)

    def test_canonical_file_never_quotes_a_project_specific_rule(self) -> None:
        document = synth.render(self.survey, min_scopes=2)
        self.assertNotIn("gate.sh", document)


class StubTransport:
    """Deterministic stand-in for Ollama, so the semantic pass is testable."""

    def __init__(self) -> None:
        self.embed_calls = 0
        self.chat_calls = 0

    def __call__(self, path: str, payload: dict) -> dict:
        if path == "/api/embed":
            self.embed_calls += 1
            text = payload["input"]
            # A crude but stable embedding: rules about the same thing share
            # words, so a bag-of-characters vector clusters them together.
            vector = [0.0] * 26
            for character in text.lower():
                if "a" <= character <= "z":
                    vector[ord(character) - 97] += 1.0
            return {"embeddings": [vector]}
        self.chat_calls += 1
        if "contradict" in payload["messages"][0]["content"]:
            return {"message": {"content": "NO"}}
        return {"message": {"content": "Invented Topic Label"}}


class EnrichmentTest(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "tree"
        self.root.mkdir()
        build_tree(self.root)
        self.cache = Path(self.tmp.name) / "cache"
        self.survey = build_survey(self.root, use_git=False)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_clustering_is_stable_for_identical_input(self) -> None:
        items = [("a", [1.0, 0.0]), ("b", [0.99, 0.1]), ("c", [0.0, 1.0])]
        self.assertEqual(cluster(items), cluster(items))
        self.assertEqual(cluster(items)["a"], cluster(items)["b"])
        self.assertNotEqual(cluster(items)["a"], cluster(items)["c"])

    def test_second_run_is_served_entirely_from_cache(self) -> None:
        stub = StubTransport()
        first = enrich(self.survey, cache_dir=self.cache, transport=stub)
        calls_after_first = stub.embed_calls + stub.chat_calls
        self.assertGreater(calls_after_first, 0)

        again = build_survey(self.root, use_git=False)
        second = enrich(again, cache_dir=self.cache, transport=stub)
        self.assertEqual(stub.embed_calls + stub.chat_calls, calls_after_first)
        self.assertEqual(second["calls"], 0)
        self.assertGreater(second["cache_hits"], 0)
        self.assertEqual(
            [c["label"] for c in first["clusters"]], [c["label"] for c in second["clusters"]]
        )

    def test_an_unreachable_model_leaves_every_number_intact(self) -> None:
        def broken(path: str, payload: dict) -> dict:
            raise OSError("no model here")

        before = self.survey.headline()
        result = enrich(self.survey, cache_dir=self.cache, transport=broken)
        self.assertEqual(self.survey.headline(), before)
        self.assertEqual(result["clusters"], [])
        self.assertGreater(result["failures"], 0)

    def test_cache_keys_separate_models(self) -> None:
        cache = Cache(self.cache)
        stub = StubTransport()
        a = Client(cache, stub, "model-a", "embed-a")
        b = Client(cache, stub, "model-b", "embed-b")
        a.ask("same prompt")
        b.ask("same prompt")
        self.assertEqual(stub.chat_calls, 2)


class EndToEndTest(unittest.TestCase):
    def test_run_py_writes_all_three_deliverables(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "tree"
            root.mkdir()
            build_tree(root)
            out = Path(tmp) / "out"
            script = Path(__file__).resolve().parents[1] / "run.py"
            result = subprocess.run(
                [sys.executable, str(script), str(root), "--out", str(out), "--no-git"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ("report.html", "AGENTS.canonical.md", "survey.json"):
                self.assertTrue((out / name).exists(), f"{name} missing")
            html = (out / "report.html").read_text()
            self.assertIn("<!doctype html>", html)
            self.assertIn("alpha", html, "unredacted run must keep the real names")
            self.assertNotIn("http://cdn", html)
            self.assertNotIn("<script", html)

    def test_redacted_run_masks_the_name_in_every_output(self) -> None:
        """--redact must reach the report, the canonical file and the JSON alike."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "tree"
            root.mkdir()
            build_tree(root)
            out = Path(tmp) / "out"
            script = Path(__file__).resolve().parents[1] / "run.py"
            result = subprocess.run(
                [sys.executable, str(script), str(root), "--out", str(out), "--no-git", "--redact", "alpha"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ("report.html", "AGENTS.canonical.md", "survey.json"):
                text = (out / name).read_text()
                self.assertNotIn("alpha", text, f"{name} leaked the name")
            self.assertIn("a████", (out / "report.html").read_text())


if __name__ == "__main__":
    unittest.main()
