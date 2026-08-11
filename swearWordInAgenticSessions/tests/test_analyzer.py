from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swearstats.analyzer import analyze, load_lexicon, parse_boundary, serialize
from swearstats.report import write_report


class AnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.lexicon_path = self.root / "words.tsv"
        self.lexicon_path.write_text(
            "heck\theck\texpletive\t1\nhecking\theck\texpletive\t1\nblast\tblast\texpletive\t2\n",
            encoding="utf-8",
        )
        self.lexicon = load_lexicon([self.lexicon_path])

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_jsonl(self, name: str, rows: list[object]) -> Path:
        path = self.root / name
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        return path

    def test_combines_both_sources_and_canonicalizes_inflections(self) -> None:
        claude = self.write_jsonl(
            "claude.jsonl",
            [
                {
                    "display": "What the HECK is this?",
                    "timestamp": 1_725_235_200_000,
                    "sessionId": "claude-a",
                    "project": "/private/project",
                },
                {
                    "display": "A clean follow-up",
                    "timestamp": 1_725_321_600_000,
                    "sessionId": "claude-a",
                },
            ],
        )
        codex = self.write_jsonl(
            "codex.jsonl",
            [
                {"text": "Hecking blast!", "ts": 1_725_408_000, "session_id": "codex-a"},
                {"text": "shellcheck is not heck", "ts": 1_725_494_400, "session_id": "codex-b"},
            ],
        )

        result = analyze([("claude", claude), ("codex", codex)], self.lexicon)
        data = serialize(result, {"claude": claude, "codex": codex}, len(self.lexicon))

        self.assertEqual(data["sources"]["all"]["totals"]["prompts"], 4)
        self.assertEqual(data["sources"]["all"]["totals"]["hits"], 4)
        self.assertEqual(data["sources"]["claude"]["totals"]["hits"], 1)
        self.assertEqual(data["sources"]["codex"]["totals"]["hits"], 3)
        self.assertEqual(data["sources"]["all"]["terms"][0], {"term": "heck", "count": 3})
        self.assertEqual(data["source_meta"]["claude"]["projects"], 1)

    def test_whole_words_avoid_substring_false_positives(self) -> None:
        codex = self.write_jsonl(
            "codex.jsonl",
            [{"text": "shellcheck shell_heck heck", "ts": 1_725_408_000, "session_id": "a"}],
        )
        result = analyze([("codex", codex)], self.lexicon)
        self.assertEqual(result.totals["all"].hits, 2)

    def test_malformed_records_are_skipped_and_counted(self) -> None:
        path = self.root / "codex.jsonl"
        path.write_text('{"text":"heck","ts":1725408000}\nnot json\n{"ts":1}\n', encoding="utf-8")
        result = analyze([("codex", path)], self.lexicon)
        self.assertEqual(result.totals["all"].prompts, 1)
        self.assertEqual(result.malformed["codex"], 2)

    def test_date_window_is_inclusive(self) -> None:
        codex = self.write_jsonl(
            "codex.jsonl",
            [
                {"text": "heck", "ts": "2024-09-01T12:00:00+00:00"},
                {"text": "blast", "ts": "2024-09-02T12:00:00+00:00"},
                {"text": "heck", "ts": "2024-09-03T12:00:00+00:00"},
            ],
        )
        result = analyze(
            [("codex", codex)],
            self.lexicon,
            since=parse_boundary("2024-09-02"),
            until=parse_boundary("2024-09-02", end=True),
        )
        self.assertEqual(result.totals["all"].prompts, 1)
        self.assertEqual(result.terms["all"]["blast"], 1)

    def test_report_does_not_embed_prompt_text_or_project_path(self) -> None:
        secret = "SUPER_SECRET_PROMPT_TEXT"
        claude = self.write_jsonl(
            "claude.jsonl",
            [
                {
                    "display": f"heck {secret}",
                    "timestamp": 1_725_235_200_000,
                    "project": "/secret/path",
                }
            ],
        )
        result = analyze([("claude", claude)], self.lexicon)
        data = serialize(result, {"claude": claude}, len(self.lexicon))
        report = self.root / "report.html"
        write_report(data, report)
        rendered = report.read_text(encoding="utf-8")
        self.assertNotIn(secret, rendered)
        self.assertNotIn("/secret/path", rendered)
        self.assertIn("Aggregate counts only", rendered)


if __name__ == "__main__":
    unittest.main()
