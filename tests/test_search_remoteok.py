from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from jobforager.search.remoteok import collect_remoteok_jobs


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


class TestCollectRemoteokJobs(unittest.TestCase):
    def _mock_response(self, payload: list | dict) -> MockResponse:
        return MockResponse(json.dumps(payload).encode("utf-8"))

    def test_collect_returns_jobs(self) -> None:
        payload = [
            {"legal": "RemoteOK is a trademark of..."},
            {
                "id": 1,
                "company": "Acme",
                "position": "Python Dev",
                "url": "https://remoteok.com/remote-jobs/1",
                "apply_url": "https://acme.com/apply",
                "location": "Worldwide",
                "salary": "$100k-$150k",
                "date": "2024-01-15T00:00:00Z",
                "description": "Build APIs.",
                "tags": ["python", "api"],
            },
        ]
        with patch(
            "jobforager.search.remoteok.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_remoteok_jobs()
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["source"], "remoteok")
        self.assertEqual(job["title"], "Python Dev")
        self.assertEqual(job["company"], "Acme")
        self.assertEqual(job["job_url"], "https://remoteok.com/remote-jobs/1")
        self.assertEqual(job["apply_url"], "https://acme.com/apply")
        self.assertEqual(job["location"], "Worldwide")
        self.assertEqual(job["remote_type"], "remote")
        self.assertEqual(job["salary_raw"], "$100k-$150k")
        self.assertIsNone(job["salary_min_usd"])
        self.assertIsNone(job["salary_max_usd"])
        self.assertEqual(job["posted_at"], "2024-01-15T00:00:00Z")
        self.assertEqual(job["external_id"], "1")
        self.assertEqual(job["description"], "Build APIs.")
        self.assertEqual(job["tags"], ["python", "api"])
        self.assertEqual(job["metadata"], {})

    def test_collect_with_tag(self) -> None:
        payload = [
            {
                "id": 2,
                "company": "Beta",
                "position": "Go Dev",
                "url": "https://remoteok.com/remote-jobs/2",
                "location": "Remote",
                "date": "2024-02-01T00:00:00Z",
                "tags": ["go"],
            }
        ]
        with patch(
            "jobforager.search.remoteok.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_remoteok_jobs(tag="go")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["metadata"], {"tag": "go"})

    def test_collect_skips_metadata(self) -> None:
        payload = [
            {"legal": "RemoteOK is a trademark..."},
            {"notice": "no id here"},
        ]
        with patch(
            "jobforager.search.remoteok.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_remoteok_jobs()
        self.assertEqual(results, [])

    def test_collect_empty_response(self) -> None:
        payload = []
        with patch(
            "jobforager.search.remoteok.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_remoteok_jobs()
        self.assertEqual(results, [])

    def test_collect_network_error(self) -> None:
        with patch(
            "jobforager.search.remoteok.urllib.request.urlopen",
            side_effect=IOError("network down"),
        ):
            results = collect_remoteok_jobs()
        self.assertEqual(results, [])

    def test_collect_missing_optional_fields(self) -> None:
        payload = [
            {
                "id": 3,
                "company": "Gamma",
                "position": "DevOps Engineer",
                "url": "https://remoteok.com/remote-jobs/3",
            }
        ]
        with patch(
            "jobforager.search.remoteok.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_remoteok_jobs()
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertIsNone(job["location"])
        self.assertIsNone(job["salary_raw"])
        self.assertIsNone(job["posted_at"])
        self.assertIsNone(job["description"])
        self.assertEqual(job["tags"], [])


if __name__ == "__main__":
    unittest.main()
