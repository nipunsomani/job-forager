from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from jobforager.search.remotive import collect_remotive_jobs, strip_html_tags


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


class TestStripHtmlTags(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(strip_html_tags(""), "")

    def test_plain_text(self) -> None:
        self.assertEqual(strip_html_tags("hello world"), "hello world")

    def test_removes_script(self) -> None:
        html = "<p>hello</p><script>alert(1)</script><p>world</p>"
        result = strip_html_tags(html)
        self.assertIn("hello", result)
        self.assertIn("world", result)
        self.assertNotIn("script", result)
        self.assertNotIn("alert", result)

    def test_removes_style(self) -> None:
        html = "<style>.red{color:red}</style><p>hello</p>"
        result = strip_html_tags(html)
        self.assertIn("hello", result)
        self.assertNotIn("style", result)

    def test_decodes_entities(self) -> None:
        self.assertEqual(strip_html_tags("&lt;div&gt;"), "")

    def test_replaces_br(self) -> None:
        result = strip_html_tags("line1<br/>line2")
        self.assertIn("\n", result)
        self.assertIn("line1", result)
        self.assertIn("line2", result)


class TestCollectRemotiveJobs(unittest.TestCase):
    def _mock_response(self, payload: dict) -> MockResponse:
        return MockResponse(json.dumps(payload).encode("utf-8"))

    def test_collect_returns_jobs(self) -> None:
        payload = {
            "jobs": [
                {
                    "id": 1,
                    "title": "  Python Dev  ",
                    "company_name": "  Acme  ",
                    "url": "https://acme.com/jobs/1",
                    "candidate_required_location": "Remote",
                    "salary": "$100k",
                    "tags": ["python"],
                    "publication_date": "2024-01-15T00:00:00Z",
                    "description": "<p>Build APIs.</p>",
                }
            ]
        }
        with patch(
            "jobforager.search.remotive.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_remotive_jobs()
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["source"], "remotive")
        self.assertEqual(job["title"], "Python Dev")
        self.assertEqual(job["company"], "Acme")
        self.assertEqual(job["job_url"], "https://acme.com/jobs/1")
        self.assertEqual(job["location"], "Remote")
        self.assertEqual(job["remote_type"], "remote")
        self.assertEqual(job["salary_raw"], "$100k")
        self.assertIsNone(job["salary_min_usd"])
        self.assertIsNone(job["salary_max_usd"])
        self.assertEqual(job["posted_at"], "2024-01-15T00:00:00Z")
        self.assertIsNone(job["apply_url"])
        self.assertEqual(job["external_id"], "1")
        self.assertEqual(job["description"], "Build APIs.")
        self.assertEqual(job["tags"], ["python"])
        self.assertEqual(job["metadata"], {"category": "software-dev"})

    def test_collect_empty_jobs(self) -> None:
        payload = {"jobs": []}
        with patch(
            "jobforager.search.remotive.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_remotive_jobs()
        self.assertEqual(results, [])

    def test_collect_missing_jobs_key(self) -> None:
        payload = {}
        with patch(
            "jobforager.search.remotive.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_remotive_jobs()
        self.assertEqual(results, [])

    def test_collect_network_error(self) -> None:
        with patch(
            "jobforager.search.remotive.urllib.request.urlopen",
            side_effect=IOError("network down"),
        ):
            results = collect_remotive_jobs()
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
