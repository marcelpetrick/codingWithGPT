"""Unit tests for main.py. No network access: the GitLab client is faked."""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import gitlab

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402


# ----------------------------- Fixtures -----------------------------


def diff_note(note_id=1, author="alice", resolved=False, body="please rename this"):
    return {
        "id": note_id,
        "system": False,
        "resolvable": True,
        "resolved": resolved,
        "body": body,
        "author": {"username": author, "name": author.title()},
        "position": {"new_path": "src/app.py", "old_path": "src/app.py"},
    }


def diff_thread(discussion_id="abc123", **kwargs):
    return {
        "id": discussion_id,
        "individual_note": False,
        "notes": [diff_note(**kwargs)],
    }


def standalone_comment(discussion_id="plain1", author="bob"):
    """A comment typed into the MR overview box: no resolved state exists."""
    return {
        "id": discussion_id,
        "individual_note": True,
        "notes": [
            {
                "id": 99,
                "system": False,
                "resolvable": False,
                "resolved": False,
                "body": "looks good to me",
                "author": {"username": author},
            }
        ],
    }


def system_note(discussion_id="sys1"):
    return {
        "id": discussion_id,
        "individual_note": True,
        "notes": [
            {
                "id": 7,
                "system": True,
                "resolvable": False,
                "body": "added 3 commits",
                "author": {"username": "carol"},
            }
        ],
    }


class FakeDiscussions:
    """Stands in for python-gitlab's ProjectMergeRequestDiscussionManager."""

    def __init__(self, discussions, errors=None):
        self._discussions = discussions
        self._errors = errors or {}
        self.updates = []

    def list(self, **kwargs):
        self.list_kwargs = kwargs
        return list(self._discussions)

    def update(self, discussion_id, new_data):
        self.updates.append((discussion_id, new_data))
        if discussion_id in self._errors:
            raise self._errors[discussion_id]
        for discussion in self._discussions:
            if discussion["id"] != discussion_id:
                continue
            updated = {
                **discussion,
                "notes": [
                    {**note, "resolved": new_data["resolved"]}
                    if note.get("resolvable")
                    else note
                    for note in discussion["notes"]
                ],
            }
            return updated
        raise AssertionError(f"unexpected discussion id {discussion_id!r}")


class FakeMergeRequest:
    def __init__(self, discussions):
        self.discussions = discussions


# ----------------------------- URL parsing -----------------------------


class ParseMergeRequestUrlTests(unittest.TestCase):
    def test_modern_url(self):
        ref = main.parse_merge_request_url(
            "https://gitlab.example.com/group/project/-/merge_requests/42"
        )
        self.assertEqual(ref.base_url, "https://gitlab.example.com")
        self.assertEqual(ref.project_path, "group/project")
        self.assertEqual(ref.mr_iid, 42)
        self.assertEqual(ref.web_url, ref.web_url)

    def test_nested_subgroups(self):
        ref = main.parse_merge_request_url(
            "https://host/a/b/c/project/-/merge_requests/7"
        )
        self.assertEqual(ref.project_path, "a/b/c/project")
        self.assertEqual(ref.mr_iid, 7)

    def test_legacy_url_without_dash_separator(self):
        ref = main.parse_merge_request_url("https://host/group/project/merge_requests/3")
        self.assertEqual(ref.project_path, "group/project")
        self.assertEqual(ref.mr_iid, 3)

    def test_trailing_subpage_query_and_fragment(self):
        ref = main.parse_merge_request_url(
            "https://host/g/p/-/merge_requests/12/diffs?view=inline#note_5"
        )
        self.assertEqual(ref.project_path, "g/p")
        self.assertEqual(ref.mr_iid, 12)

    def test_port_is_preserved(self):
        ref = main.parse_merge_request_url("https://host:8443/g/p/-/merge_requests/1")
        self.assertEqual(ref.base_url, "https://host:8443")

    def test_surrounding_whitespace_is_tolerated(self):
        ref = main.parse_merge_request_url("  https://host/g/p/-/merge_requests/1\n")
        self.assertEqual(ref.mr_iid, 1)

    def test_subpath_instance_requires_base_url(self):
        """Without the hint, the subpath is indistinguishable from a namespace."""
        naive = main.parse_merge_request_url("https://host/gitlab/g/p/-/merge_requests/1")
        self.assertEqual(naive.project_path, "gitlab/g/p")

        ref = main.parse_merge_request_url(
            "https://host/gitlab/g/p/-/merge_requests/1",
            base_url_hint="https://host/gitlab",
        )
        self.assertEqual(ref.base_url, "https://host/gitlab")
        self.assertEqual(ref.project_path, "g/p")
        self.assertEqual(ref.web_url, "https://host/gitlab/g/p/-/merge_requests/1")

    def test_base_url_host_mismatch_is_rejected(self):
        with self.assertRaises(main.MergeRequestUrlError):
            main.parse_merge_request_url(
                "https://host-a/g/p/-/merge_requests/1",
                base_url_hint="https://host-b",
            )

    def test_base_url_path_mismatch_is_rejected(self):
        with self.assertRaises(main.MergeRequestUrlError):
            main.parse_merge_request_url(
                "https://host/other/g/p/-/merge_requests/1",
                base_url_hint="https://host/gitlab",
            )

    def test_rejects_non_merge_request_url(self):
        with self.assertRaises(main.MergeRequestUrlError):
            main.parse_merge_request_url("https://host/group/project/-/issues/42")

    def test_rejects_merge_request_list_without_iid(self):
        with self.assertRaises(main.MergeRequestUrlError):
            main.parse_merge_request_url("https://host/group/project/-/merge_requests")

    def test_rejects_missing_scheme(self):
        with self.assertRaises(main.MergeRequestUrlError):
            main.parse_merge_request_url("host/group/project/-/merge_requests/1")

    def test_rejects_url_without_project_path(self):
        with self.assertRaises(main.MergeRequestUrlError):
            main.parse_merge_request_url("https://host/-/merge_requests/1")


# ----------------------------- Classification -----------------------------


class ClassifyDiscussionTests(unittest.TestCase):
    def test_open_diff_thread(self):
        info = main.classify_discussion(diff_thread())
        self.assertTrue(info.resolvable)
        self.assertFalse(info.resolved)
        self.assertEqual(info.author, "alice")
        self.assertEqual(info.file_path, "src/app.py")
        self.assertEqual(info.snippet, "please rename this")

    def test_resolved_diff_thread(self):
        info = main.classify_discussion(diff_thread(resolved=True))
        self.assertTrue(info.resolved)

    def test_thread_counts_as_open_when_any_note_is_unresolved(self):
        discussion = {
            "id": "d",
            "individual_note": False,
            "notes": [
                diff_note(note_id=1, resolved=True),
                diff_note(note_id=2, resolved=False),
            ],
        }
        info = main.classify_discussion(discussion)
        self.assertTrue(info.resolvable)
        self.assertFalse(info.resolved)

    def test_standalone_comment_is_not_resolvable(self):
        info = main.classify_discussion(standalone_comment())
        self.assertFalse(info.resolvable)
        self.assertTrue(info.individual_note)
        self.assertFalse(info.system)

    def test_system_note_is_detected(self):
        info = main.classify_discussion(system_note())
        self.assertTrue(info.system)
        self.assertFalse(info.resolvable)

    def test_author_comes_from_first_human_note(self):
        discussion = {
            "id": "d",
            "individual_note": False,
            "notes": [
                {"id": 1, "system": True, "body": "x", "author": {"username": "bot"}},
                diff_note(note_id=2, author="dana"),
            ],
        }
        self.assertEqual(main.classify_discussion(discussion).author, "dana")

    def test_missing_and_odd_fields_do_not_crash(self):
        info = main.classify_discussion({"id": "d"})
        self.assertFalse(info.resolvable)
        self.assertIsNone(info.author)
        self.assertEqual(info.note_count, 0)

        info = main.classify_discussion(
            {"id": "d", "notes": [{"id": 1, "position": "unexpected-string"}]}
        )
        self.assertIsNone(info.file_path)

    def test_snippet_is_collapsed_and_truncated(self):
        info = main.classify_discussion(diff_thread(body="a\n\n b   c " + "x" * 200))
        self.assertLessEqual(len(info.snippet), main.SNIPPET_LENGTH)
        self.assertTrue(info.snippet.endswith("…"))
        self.assertTrue(info.snippet.startswith("a b c"))


# ----------------------------- Selection -----------------------------


def infos(*discussions):
    return [main.classify_discussion(discussion) for discussion in discussions]


class SelectThreadsTests(unittest.TestCase):
    def test_selects_only_open_resolvable_threads(self):
        selection = main.select_threads(
            infos(
                diff_thread("open1"),
                diff_thread("done1", resolved=True),
                standalone_comment(),
                system_note(),
            ),
            target_resolved=True,
        )
        self.assertEqual([t.discussion_id for t in selection.selected], ["open1"])
        reasons = {t.discussion_id: reason for t, reason in selection.skipped}
        self.assertEqual(reasons["done1"], "already resolved")
        self.assertIn("standalone comment", reasons["plain1"])
        self.assertIn("system note", reasons["sys1"])

    def test_unresolve_inverts_the_target(self):
        selection = main.select_threads(
            infos(diff_thread("open1"), diff_thread("done1", resolved=True)),
            target_resolved=False,
        )
        self.assertEqual([t.discussion_id for t in selection.selected], ["done1"])
        self.assertEqual(selection.skipped[0][1], "already unresolved")

    def test_author_filter_is_case_insensitive_and_ignores_at_sign(self):
        selection = main.select_threads(
            infos(diff_thread("a", author="Alice"), diff_thread("b", author="bob")),
            target_resolved=True,
            authors=["@ALICE"],
        )
        self.assertEqual([t.discussion_id for t in selection.selected], ["a"])
        self.assertEqual(selection.skipped[0][1], "excluded by --author")

    def test_exclude_author_filter(self):
        selection = main.select_threads(
            infos(diff_thread("a", author="alice"), diff_thread("b", author="bob")),
            target_resolved=True,
            exclude_authors=["bob"],
        )
        self.assertEqual([t.discussion_id for t in selection.selected], ["a"])

    def test_max_limits_selection_and_records_the_rest(self):
        selection = main.select_threads(
            infos(diff_thread("a"), diff_thread("b"), diff_thread("c")),
            target_resolved=True,
            limit=2,
        )
        self.assertEqual([t.discussion_id for t in selection.selected], ["a", "b"])
        self.assertEqual(selection.skipped, [(selection.skipped[0][0], "beyond --max 2")])

    def test_empty_input(self):
        selection = main.select_threads([], target_resolved=True)
        self.assertEqual(selection.selected, [])
        self.assertEqual(selection.skipped, [])


# ----------------------------- Apply -----------------------------


def update_error(code):
    error = gitlab.exceptions.GitlabUpdateError("boom")
    error.response_code = code
    return error


class ApplyResolutionTests(unittest.TestCase):
    def test_resolves_each_selected_thread(self):
        discussions = FakeDiscussions([diff_thread("a"), diff_thread("b")])
        merge_request = FakeMergeRequest(discussions)
        threads = main.fetch_threads(merge_request)

        outcomes = main.apply_resolution(merge_request, threads, True)

        self.assertEqual(
            discussions.updates,
            [("a", {"resolved": True}), ("b", {"resolved": True})],
        )
        self.assertEqual([o.status for o in outcomes], ["changed", "changed"])

    def test_unresolve_sends_false(self):
        discussions = FakeDiscussions([diff_thread("a", resolved=True)])
        merge_request = FakeMergeRequest(discussions)
        threads = main.fetch_threads(merge_request)

        main.apply_resolution(merge_request, threads, False)

        self.assertEqual(discussions.updates, [("a", {"resolved": False})])

    def test_one_failure_does_not_abort_the_rest(self):
        discussions = FakeDiscussions(
            [diff_thread("a"), diff_thread("b"), diff_thread("c")],
            errors={"b": update_error(403)},
        )
        merge_request = FakeMergeRequest(discussions)
        threads = main.fetch_threads(merge_request)

        outcomes = main.apply_resolution(merge_request, threads, True)

        self.assertEqual([o.status for o in outcomes], ["changed", "failed", "changed"])
        self.assertIn("Developer role", outcomes[1].detail)

    def test_404_is_explained(self):
        discussions = FakeDiscussions(
            [diff_thread("a")], errors={"a": update_error(404)}
        )
        merge_request = FakeMergeRequest(discussions)
        outcomes = main.apply_resolution(
            merge_request, main.fetch_threads(merge_request), True
        )
        self.assertIn("deleted", outcomes[0].detail)

    def test_silent_no_op_is_reported(self):
        """A 200 that did not actually change anything must not count as success."""

        class StubbornDiscussions(FakeDiscussions):
            def update(self, discussion_id, new_data):
                self.updates.append((discussion_id, new_data))
                return diff_thread(discussion_id, resolved=False)

        discussions = StubbornDiscussions([diff_thread("a")])
        merge_request = FakeMergeRequest(discussions)
        outcomes = main.apply_resolution(
            merge_request, main.fetch_threads(merge_request), True
        )
        self.assertEqual(outcomes[0].status, "no-op")

    def test_unverifiable_response_counts_as_changed(self):
        class TerseDiscussions(FakeDiscussions):
            def update(self, discussion_id, new_data):
                self.updates.append((discussion_id, new_data))
                return None

        discussions = TerseDiscussions([diff_thread("a")])
        merge_request = FakeMergeRequest(discussions)
        outcomes = main.apply_resolution(
            merge_request, main.fetch_threads(merge_request), True
        )
        self.assertEqual(outcomes[0].status, "changed")

    def test_fetch_threads_requests_all_pages(self):
        discussions = FakeDiscussions([diff_thread("a")])
        main.fetch_threads(FakeMergeRequest(discussions))
        self.assertTrue(discussions.list_kwargs.get("get_all"))


# ----------------------------- Token handling -----------------------------


class ReadTokenTests(unittest.TestCase):
    def setUp(self):
        self.warnings = []

    def warn(self, message):
        self.warnings.append(message)

    def test_reads_environment_variable(self):
        with mock.patch.dict(os.environ, {"GITLAB_TOKEN": " glpat-secret "}):
            self.assertEqual(main.read_token(None, self.warn), "glpat-secret")

    def test_missing_token_is_a_usage_failure(self):
        with mock.patch.dict(os.environ, {"GITLAB_TOKEN": ""}):
            with self.assertRaises(main.Failure) as caught:
                main.read_token(None, self.warn)
        self.assertEqual(caught.exception.code, main.EXIT_USAGE)

    def test_token_file_takes_precedence_over_environment(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("glpat-from-file\n")
            path = handle.name
        self.addCleanup(os.unlink, path)
        os.chmod(path, 0o600)

        with mock.patch.dict(os.environ, {"GITLAB_TOKEN": "glpat-from-env"}):
            self.assertEqual(main.read_token(path, self.warn), "glpat-from-file")
        self.assertEqual(self.warnings, [])

    def test_world_readable_token_file_warns(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("glpat-x")
            path = handle.name
        self.addCleanup(os.unlink, path)
        os.chmod(path, 0o644)

        main.read_token(path, self.warn)

        self.assertEqual(len(self.warnings), 1)
        self.assertIn("readable by other users", self.warnings[0])

    def test_empty_token_file_is_rejected(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("   \n")
            path = handle.name
        self.addCleanup(os.unlink, path)
        with self.assertRaises(main.Failure):
            main.read_token(path, self.warn)

    def test_unreadable_token_file_is_rejected(self):
        with self.assertRaises(main.Failure):
            main.read_token("/nonexistent/token.txt", self.warn)


# ----------------------------- CLI -----------------------------


class MainTests(unittest.TestCase):
    """Drive main() end to end with the GitLab client patched out."""

    def run_main(self, argv, discussions, isatty=False, answer=None):
        self.fake_discussions = FakeDiscussions(discussions)
        merge_request = FakeMergeRequest(self.fake_discussions)
        client = mock.Mock()
        client.user.username = "tester"

        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"GITLAB_TOKEN": "glpat-x"}), \
             mock.patch.object(main, "build_client", return_value=client), \
             mock.patch.object(main, "fetch_merge_request", return_value=merge_request), \
             mock.patch.object(sys.stdin, "isatty", return_value=isatty), \
             mock.patch.object(main, "confirm", return_value=answer):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    URL = "https://host/g/p/-/merge_requests/1"

    def test_dry_run_writes_nothing(self):
        code, out, _ = self.run_main(
            [self.URL, "--dry-run"], [diff_thread("a"), standalone_comment()]
        )
        self.assertEqual(code, main.EXIT_OK)
        self.assertEqual(self.fake_discussions.updates, [])
        self.assertIn("Dry run", out)

    def test_yes_resolves_without_prompting(self):
        code, out, _ = self.run_main([self.URL, "--yes"], [diff_thread("a")])
        self.assertEqual(code, main.EXIT_OK)
        self.assertEqual(self.fake_discussions.updates, [("a", {"resolved": True})])
        self.assertIn("Resolved 1/1", out)

    def test_refuses_to_write_unattended_without_yes(self):
        code, _, err = self.run_main([self.URL], [diff_thread("a")], isatty=False)
        self.assertEqual(code, main.EXIT_USAGE)
        self.assertEqual(self.fake_discussions.updates, [])
        self.assertIn("--yes", err)

    def test_declining_the_prompt_aborts(self):
        code, out, _ = self.run_main(
            [self.URL], [diff_thread("a")], isatty=True, answer=False
        )
        self.assertEqual(code, main.EXIT_ABORTED)
        self.assertEqual(self.fake_discussions.updates, [])
        self.assertIn("Aborted", out)

    def test_accepting_the_prompt_applies(self):
        code, _, _ = self.run_main(
            [self.URL], [diff_thread("a")], isatty=True, answer=True
        )
        self.assertEqual(code, main.EXIT_OK)
        self.assertEqual(self.fake_discussions.updates, [("a", {"resolved": True})])

    def test_nothing_to_do_is_success(self):
        code, out, _ = self.run_main(
            [self.URL, "--yes"], [diff_thread("a", resolved=True), standalone_comment()]
        )
        self.assertEqual(code, main.EXIT_OK)
        self.assertEqual(self.fake_discussions.updates, [])
        self.assertIn("Nothing to resolve", out)

    def test_partial_failure_exit_code(self):
        self.fake_discussions = None
        discussions = FakeDiscussions(
            [diff_thread("a"), diff_thread("b")], errors={"b": update_error(403)}
        )
        merge_request = FakeMergeRequest(discussions)
        client = mock.Mock()
        client.user.username = "tester"
        with mock.patch.dict(os.environ, {"GITLAB_TOKEN": "glpat-x"}), \
             mock.patch.object(main, "build_client", return_value=client), \
             mock.patch.object(main, "fetch_merge_request", return_value=merge_request):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = main.main([self.URL, "--yes"])
        self.assertEqual(code, main.EXIT_PARTIAL_FAILURE)

    def test_bad_url_is_a_usage_error(self):
        code, _, err = self.run_main([
            "https://host/g/p/-/issues/1", "--dry-run"
        ], [])
        self.assertEqual(code, main.EXIT_USAGE)
        self.assertIn("merge request", err)

    def test_invalid_max_is_rejected(self):
        code, _, err = self.run_main([self.URL, "--max", "0", "--dry-run"], [])
        self.assertEqual(code, main.EXIT_USAGE)
        self.assertIn("--max", err)

    def test_conflicting_tls_options_are_rejected(self):
        code, _, err = self.run_main(
            [self.URL, "--no-verify-ssl", "--ca-bundle", "/tmp/ca.pem", "--dry-run"], []
        )
        self.assertEqual(code, main.EXIT_USAGE)
        self.assertIn("mutually exclusive", err)

    def test_json_output_keeps_stdout_parseable(self):
        import json as json_module

        code, out, err = self.run_main(
            [self.URL, "--json", "--yes"], [diff_thread("a"), standalone_comment()]
        )
        self.assertEqual(code, main.EXIT_OK)
        payload = json_module.loads(out)
        self.assertEqual(payload["action"], "resolve")
        self.assertEqual(len(payload["selected"]), 1)
        self.assertEqual(payload["outcomes"][0]["status"], "changed")
        self.assertIn("Merge request", err)  # human text went to stderr

    def test_show_skipped_lists_each_thread(self):
        _, out, _ = self.run_main(
            [self.URL, "--dry-run", "--show-skipped"],
            [diff_thread("a"), standalone_comment(), system_note()],
        )
        self.assertIn("standalone comment", out)
        self.assertIn("system note", out)
        self.assertNotIn("×", out)  # the aggregated summary must not appear

    def test_skipped_summary_is_aggregated_by_default(self):
        _, out, _ = self.run_main(
            [self.URL, "--dry-run"],
            [diff_thread("a"), standalone_comment("p1"), standalone_comment("p2")],
        )
        self.assertIn("2 ×", out)


if __name__ == "__main__":
    unittest.main()
