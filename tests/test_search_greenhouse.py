from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from jobforager.search.greenhouse import collect_greenhouse_jobs


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


class TestCollectGreenhouseJobs(unittest.TestCase):
    def _mock_response(self, payload: dict) -> MockResponse:
        return MockResponse(json.dumps(payload).encode("utf-8"))

    def test_collect_returns_jobs(self) -> None:
        payload = {
            "jobs": [
                {
                    "id": 123,
                    "internal_job_id": 456,
                    "title": "Software Engineer",
                    "absolute_url": "https://boards.greenhouse.io/stripe/jobs/123",
                    "location": {"name": "San Francisco, CA"},
                    "updated_at": "2024-01-15T09:00:00-05:00",
                    "first_published": "2024-01-10T09:00:00-05:00",
                    "requisition_id": "REQ-001",
                    "company_name": "Stripe",
                    "metadata": [
                        {"name": "Workplace Type", "value": "Remote", "value_type": "single_select"}
                    ],
                }
            ]
        }
        with patch(
            "jobforager.search.greenhouse.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.greenhouse.time.sleep"):
                results = collect_greenhouse_jobs(board_tokens=["stripe"], delay=0)
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["source"], "greenhouse")
        self.assertEqual(job["title"], "Software Engineer")
        self.assertEqual(job["company"], "Stripe")
        self.assertEqual(job["job_url"], "https://boards.greenhouse.io/stripe/jobs/123")
        self.assertEqual(job["location"], "San Francisco, CA")
        self.assertEqual(job["remote_type"], "remote")
        self.assertIsNone(job["salary_raw"])
        self.assertIsNone(job["salary_min_usd"])
        self.assertIsNone(job["salary_max_usd"])
        self.assertEqual(job["posted_at"], "2024-01-10T09:00:00-05:00")
        self.assertIsNone(job["apply_url"])
        self.assertEqual(job["external_id"], "123")
        self.assertIsNone(job["description"])
        self.assertEqual(job["tags"], [])
        self.assertEqual(job["metadata"]["board_token"], "stripe")
        self.assertEqual(job["metadata"]["requisition_id"], "REQ-001")

    def test_collect_with_content(self) -> None:
        payload = {
            "jobs": [
                {
                    "id": 789,
                    "title": "Product Manager",
                    "absolute_url": "https://boards.greenhouse.io/airbnb/jobs/789",
                    "location": {"name": "Paris, France"},
                    "updated_at": "2024-02-01T10:00:00-05:00",
                    "content": "<p>Lead product.</p>",
                    "company_name": "Airbnb",
                    "metadata": [],
                }
            ]
        }
        with patch(
            "jobforager.search.greenhouse.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.greenhouse.time.sleep"):
                results = collect_greenhouse_jobs(
                    board_tokens=["airbnb"], include_content=True, delay=0
                )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["description"], "<p>Lead product.</p>")

    def test_collect_empty_jobs(self) -> None:
        payload = {"jobs": []}
        with patch(
            "jobforager.search.greenhouse.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.greenhouse.time.sleep"):
                results = collect_greenhouse_jobs(board_tokens=["figma"], delay=0)
        self.assertEqual(results, [])

    def test_collect_network_error(self) -> None:
        with patch(
            "jobforager.search.greenhouse.urllib.request.urlopen",
            side_effect=IOError("network down"),
        ):
            with patch("jobforager.search.greenhouse.time.sleep"):
                results = collect_greenhouse_jobs(board_tokens=["anthropic"], delay=0)
        self.assertEqual(results, [])

    def test_collect_multiple_boards(self) -> None:
        call_count = 0
        def mock_urlopen(req, **kwargs):
            nonlocal call_count
            call_count += 1
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            if "stripe" in url:
                return MockResponse(
                    json.dumps({"jobs": [{"id": 1, "title": "Eng", "absolute_url": "https://example.com/1", "location": {"name": "SF"}, "updated_at": "2024-01-01", "company_name": "Stripe", "metadata": []}]}).encode("utf-8")
                )
            if "airbnb" in url:
                return MockResponse(
                    json.dumps({"jobs": [{"id": 2, "title": "PM", "absolute_url": "https://example.com/2", "location": {"name": "NY"}, "updated_at": "2024-01-02", "company_name": "Airbnb", "metadata": []}]}).encode("utf-8")
                )
            return MockResponse(b"{}")

        with patch(
            "jobforager.search.greenhouse.urllib.request.urlopen",
            side_effect=mock_urlopen,
        ):
            with patch("jobforager.search.greenhouse.time.sleep"):
                results = collect_greenhouse_jobs(board_tokens=["stripe", "airbnb"], delay=0)
        self.assertEqual(len(results), 2)
        companies = {r["company"] for r in results}
        self.assertEqual(companies, {"Stripe", "Airbnb"})


if __name__ == "__main__":
    unittest.main()
