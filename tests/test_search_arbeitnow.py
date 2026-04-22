from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from jobforager.search.arbeitnow import collect_arbeitnow_jobs


class MockResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def info(self):
        class _Info:
            def get_content_charset(self, default="utf-8"):
                return default
        return _Info()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class TestCollectArbeitnowJobs(unittest.TestCase):
    def _mock_response(self, payload: list | dict) -> MockResponse:
        return MockResponse(json.dumps(payload).encode("utf-8"))

    def test_collect_returns_jobs(self) -> None:
        payload = [
            {
                "title": "Python Developer",
                "company_name": "Acme GmbH",
                "url": "https://arbeitnow.com/view/python-dev-acme",
                "location": "Berlin, Germany",
                "remote": True,
                "date": "2024-01-15T00:00:00Z",
                "slug": "python-dev-acme",
                "description": "Build APIs in Berlin.",
                "tags": ["python", "django"],
            }
        ]
        with patch(
            "jobforager.search.arbeitnow.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_arbeitnow_jobs()
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["source"], "arbeitnow")
        self.assertEqual(job["title"], "Python Developer")
        self.assertEqual(job["company"], "Acme GmbH")
        self.assertEqual(job["job_url"], "https://arbeitnow.com/view/python-dev-acme")
        self.assertEqual(job["location"], "Berlin, Germany")
        self.assertEqual(job["remote_type"], "remote")
        self.assertIsNone(job["salary_raw"])
        self.assertIsNone(job["salary_min_usd"])
        self.assertIsNone(job["salary_max_usd"])
        self.assertEqual(job["posted_at"], "2024-01-15T00:00:00Z")
        self.assertIsNone(job["apply_url"])
        self.assertEqual(job["external_id"], "python-dev-acme")
        self.assertEqual(job["description"], "Build APIs in Berlin.")
        self.assertEqual(job["tags"], ["python", "django"])
        self.assertEqual(job["metadata"], {})

    def test_collect_remote_false(self) -> None:
        payload = [
            {
                "title": "Onsite Engineer",
                "company_name": "Beta",
                "url": "https://arbeitnow.com/view/onsite",
                "location": "Munich",
                "remote": False,
                "date": "2024-02-01T00:00:00Z",
                "slug": "onsite",
            }
        ]
        with patch(
            "jobforager.search.arbeitnow.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_arbeitnow_jobs()
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0]["remote_type"])

    def test_collect_empty_response(self) -> None:
        payload = []
        with patch(
            "jobforager.search.arbeitnow.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_arbeitnow_jobs()
        self.assertEqual(results, [])

    def test_collect_network_error(self) -> None:
        with patch(
            "jobforager.search.arbeitnow.urllib.request.urlopen",
            side_effect=IOError("network down"),
        ):
            results = collect_arbeitnow_jobs()
        self.assertEqual(results, [])

    def test_collect_missing_optional_fields(self) -> None:
        payload = [
            {
                "title": "DevOps",
                "company_name": "Gamma",
                "url": "https://arbeitnow.com/view/devops",
                "remote": True,
            }
        ]
        with patch(
            "jobforager.search.arbeitnow.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_arbeitnow_jobs()
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertIsNone(job["location"])
        self.assertIsNone(job["posted_at"])
        self.assertIsNone(job["external_id"])
        self.assertIsNone(job["description"])
        self.assertEqual(job["tags"], [])


if __name__ == "__main__":
    unittest.main()
