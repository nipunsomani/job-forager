from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from jobforager.search.lever import collect_lever_jobs


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


class TestCollectLeverJobs(unittest.TestCase):
    def _mock_response(self, payload: list | dict) -> MockResponse:
        return MockResponse(json.dumps(payload).encode("utf-8"))

    def test_collect_returns_jobs(self) -> None:
        payload = [
            {
                "id": "abc-123",
                "text": "Senior Engineer",
                "categories": {
                    "location": "San Francisco, CA",
                    "commitment": "Full-time",
                    "team": "Platform",
                    "department": "Engineering",
                },
                "country": "US",
                "workplaceType": "remote",
                "createdAt": 1705276800000,
                "hostedUrl": "https://jobs.lever.co/netflix/abc-123",
                "applyUrl": "https://jobs.lever.co/netflix/abc-123/apply",
                "descriptionPlain": "Build scalable systems.",
                "salaryRange": {
                    "currency": "USD",
                    "interval": "yearly",
                    "min": 180000,
                    "max": 250000,
                },
            }
        ]
        with patch(
            "jobforager.search.lever.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.lever.time.sleep"):
                results = collect_lever_jobs(company_slugs=["netflix"], delay=0)
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["source"], "lever")
        self.assertEqual(job["title"], "Senior Engineer")
        self.assertEqual(job["company"], "netflix")
        self.assertEqual(job["job_url"], "https://jobs.lever.co/netflix/abc-123")
        self.assertEqual(job["location"], "San Francisco, CA")
        self.assertEqual(job["remote_type"], "remote")
        self.assertEqual(job["salary_raw"], "USD 180000-250000 / yearly")
        self.assertEqual(job["salary_min_usd"], 180000)
        self.assertEqual(job["salary_max_usd"], 250000)
        self.assertEqual(job["apply_url"], "https://jobs.lever.co/netflix/abc-123/apply")
        self.assertEqual(job["external_id"], "abc-123")
        self.assertEqual(job["description"], "Build scalable systems.")
        self.assertEqual(sorted(job["tags"]), ["Engineering", "Full-time", "Platform"])
        self.assertEqual(job["metadata"]["company_slug"], "netflix")

    def test_collect_onsite_workplace(self) -> None:
        payload = [
            {
                "id": "def-456",
                "text": "Designer",
                "categories": {"location": "New York, NY"},
                "workplaceType": "on-site",
                "createdAt": 1705276800000,
                "hostedUrl": "https://jobs.lever.co/shopify/def-456",
            }
        ]
        with patch(
            "jobforager.search.lever.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.lever.time.sleep"):
                results = collect_lever_jobs(company_slugs=["shopify"], delay=0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["remote_type"], "onsite")

    def test_collect_empty_response(self) -> None:
        payload = []
        with patch(
            "jobforager.search.lever.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.lever.time.sleep"):
                results = collect_lever_jobs(company_slugs=["airbnb"], delay=0)
        self.assertEqual(results, [])

    def test_collect_network_error(self) -> None:
        with patch(
            "jobforager.search.lever.urllib.request.urlopen",
            side_effect=IOError("network down"),
        ):
            with patch("jobforager.search.lever.time.sleep"):
                results = collect_lever_jobs(company_slugs=["leverdemo"], delay=0)
        self.assertEqual(results, [])

    def test_collect_missing_optional_fields(self) -> None:
        payload = [
            {
                "id": "ghi-789",
                "text": "Manager",
                "categories": {},
                "createdAt": 1705276800000,
                "hostedUrl": "https://jobs.lever.co/demo/ghi-789",
            }
        ]
        with patch(
            "jobforager.search.lever.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.lever.time.sleep"):
                results = collect_lever_jobs(company_slugs=["demo"], delay=0)
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertIsNone(job["location"])
        self.assertIsNone(job["remote_type"])
        self.assertIsNone(job["salary_raw"])
        self.assertIsNone(job["apply_url"])
        self.assertEqual(job["tags"], [])


if __name__ == "__main__":
    unittest.main()
