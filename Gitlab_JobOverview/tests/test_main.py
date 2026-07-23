import unittest
from types import SimpleNamespace

import main


class RecordingJobs:
    def __init__(self, jobs=None):
        self.jobs = jobs or []
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
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
                verbose=False,
            )
        )

        self.assertEqual([first, second], result)
        self.assertEqual(["group/first", "group/second"], projects.get_calls)


if __name__ == "__main__":
    unittest.main()
