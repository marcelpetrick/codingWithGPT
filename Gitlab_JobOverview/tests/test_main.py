import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from types import SimpleNamespace

import gitlab

import main


class RecordingJobs:
    def __init__(self, jobs=None, error=None):
        self.jobs = jobs or []
        self.error = error
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.jobs


class RecordingProjects:
    def __init__(self, listed=None, selected=None):
        self.listed = listed or []
        self.selected = selected or {}
        self.list_calls = []
        self.get_calls = []

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return iter(self.listed)

    def get(self, path):
        self.get_calls.append(path)
        return self.selected[path]


class FetchJobsTests(unittest.TestCase):
    def test_running_and_pending_are_fetched_in_one_request(self):
        jobs = RecordingJobs()
        project = SimpleNamespace(
            id=42,
            path_with_namespace="group/project",
            web_url="https://gitlab.example/group/project",
            jobs=jobs,
        )

        project_id, path, result = main.fetch_jobs_for_project(project)

        self.assertEqual("42", project_id)
        self.assertEqual("group/project", path)
        self.assertEqual([], result)
        self.assertEqual(
            [
                {
                    "scope": ["running", "pending"],
                    "per_page": 100,
                    "get_all": True,
                }
            ],
            jobs.calls,
        )

    def test_single_requested_status_uses_one_scope(self):
        jobs = RecordingJobs()
        project = SimpleNamespace(
            id=42,
            path_with_namespace="group/project",
            web_url="https://gitlab.example/group/project",
            jobs=jobs,
        )

        main.fetch_jobs_for_project(
            project,
            want_running=False,
            want_pending=True,
        )

        self.assertEqual(["pending"], jobs.calls[0]["scope"])

    def test_list_errors_propagate_to_the_scan_coordinator(self):
        jobs = RecordingJobs(
            error=gitlab.exceptions.GitlabListError(
                "forbidden",
                response_code=403,
            )
        )
        project = SimpleNamespace(
            id=42,
            path_with_namespace="group/project",
            web_url="https://gitlab.example/group/project",
            jobs=jobs,
        )

        with self.assertRaises(gitlab.exceptions.GitlabListError):
            main.fetch_jobs_for_project(project)


class ProjectDiscoveryTests(unittest.TestCase):
    def test_membership_listing_requests_simple_project_records(self):
        project = SimpleNamespace(path_with_namespace="group/project")
        projects = RecordingProjects(listed=[project])
        gl = SimpleNamespace(projects=projects)

        result = list(
            main.iter_projects(
                gl,
                include_archived=False,
                limit=None,
                verbose=False,
            )
        )

        self.assertEqual([project], result)
        self.assertTrue(projects.list_calls[0]["simple"])
        self.assertFalse(projects.list_calls[0]["archived"])

    def test_including_archived_projects_omits_the_archive_filter(self):
        projects = RecordingProjects()
        gl = SimpleNamespace(projects=projects)

        list(
            main.iter_projects(
                gl,
                include_archived=True,
                limit=None,
                verbose=False,
            )
        )

        self.assertNotIn("archived", projects.list_calls[0])

    def test_selected_projects_are_resolved_directly_and_deduplicated_by_caller(self):
        first = SimpleNamespace(archived=False)
        second = SimpleNamespace(archived=False)
        projects = RecordingProjects(
            selected={
                "group/first": first,
                "group/second": second,
            }
        )
        gl = SimpleNamespace(projects=projects)

        result = list(
            main.iter_selected_projects(
                gl,
                ["group/first", "group/second"],
                include_archived=False,
                limit=None,
            )
        )

        self.assertEqual([first, second], result)
        self.assertEqual(["group/first", "group/second"], projects.get_calls)


class OutputTests(unittest.TestCase):
    def test_table_reports_failed_project_count(self):
        output = StringIO()

        with redirect_stdout(output):
            main.print_table(
                {
                    "group/success": [],
                    "group/failure": [],
                },
                "https://gitlab.example",
                "user",
                failed_projects=1,
            )

        self.assertIn("Projects scanned: 2 (failed: 1)", output.getvalue())

    def test_elapsed_time_preserves_millisecond_precision(self):
        self.assertEqual("1m2.346s", main.human_elapsed(62.3456))

    def test_table_elapsed_time_is_printed_to_stdout(self):
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            main.print_elapsed(1.25, "table")

        self.assertEqual("Elapsed wall-clock time: 1.250s\n", stdout.getvalue())
        self.assertEqual("", stderr.getvalue())

    def test_json_elapsed_time_is_printed_to_stderr(self):
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            main.print_elapsed(1.25, "json")

        self.assertEqual("", stdout.getvalue())
        self.assertEqual("Elapsed wall-clock time: 1.250s\n", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
