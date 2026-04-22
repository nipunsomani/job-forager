from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from jobforager.search.smartrecruiters import collect_smartrecruiters_jobs


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


class TestCollectSmartRecruitersJobs(unittest.TestCase):
    def _mock_response(self, payload: dict) -> MockResponse:
        return MockResponse(json.dumps(payload).encode("utf-8"))

    def test_collect_returns_jobs(self) -> None:
        payload = {
            "content": [
                {
                    "id": "job-123",
                    "name": "Senior Engineer",
                    "company": {"name": "Adobe"},
                    "location": {"city": "San Francisco", "country": "US"},
                    "postingUrl": "https://jobs.smartrecruiters.com/adobe1/job-123",
                    "createdOn": "2024-01-15T09:00:00Z",
                    "refNumber": "REF-001",
                    "jobAd": {
                        "sections": {
                            "jobDescription": {"text": "Build great products."}
                        }
                    },
                    "typeOfEmployment": {"label": "Full-time"},
                }
            ],
            "totalFound": 1,
        }
        with patch(
            "jobforager.search.smartrecruiters.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.smartrecruiters.time.sleep"):
                results = collect_smartrecruiters_jobs(company_slugs=["adobe1"], delay=0)
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["source"], "smartrecruiters")
        self.assertEqual(job["title"], "Senior Engineer")
        self.assertEqual(job["company"], "Adobe")
        self.assertEqual(
            job["job_url"], "https://jobs.smartrecruiters.com/adobe1/job-123"
        )
        self.assertEqual(job["location"], "San Francisco, US")
        self.assertIsNone(job["remote_type"])
        self.assertIsNone(job["salary_raw"])
        self.assertIsNone(job["salary_min_usd"])
        self.assertIsNone(job["salary_max_usd"])
        self.assertEqual(job["posted_at"], "2024-01-15T09:00:00Z")
        self.assertIsNone(job["apply_url"])
        self.assertEqual(job["external_id"], "job-123")
        self.assertEqual(job["description"], "Build great products.")
        self.assertEqual(job["tags"], ["Full-time"])
        self.assertEqual(job["metadata"]["company_slug"], "adobe1")
        self.assertEqual(job["metadata"]["ref_number"], "REF-001")

    def test_collect_pagination(self) -> None:
        call_count = 0

        def mock_urlopen(req, **kwargs):
            nonlocal call_count
            call_count += 1
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            if "offset=0" in url:
                return MockResponse(
                    json.dumps(
                        {
                            "content": [
                                {"id": str(i), "name": f"Job {i}", "postingUrl": f"https://example.com/{i}"}
                                for i in range(1, 101)
                            ],
                            "totalFound": 150,
                        }
                    ).encode("utf-8")
                )
            if "offset=100" in url:
                return MockResponse(
                    json.dumps(
                        {
                            "content": [
                                {"id": str(i), "name": f"Job {i}", "postingUrl": f"https://example.com/{i}"}
                                for i in range(101, 151)
                            ],
                            "totalFound": 150,
                        }
                    ).encode("utf-8")
                )
            return MockResponse(b"{}")

        with patch(
            "jobforager.search.smartrecruiters.urllib.request.urlopen",
            side_effect=mock_urlopen,
        ):
            with patch("jobforager.search.smartrecruiters.time.sleep"):
                results = collect_smartrecruiters_jobs(company_slugs=["demo"], delay=0)
        self.assertEqual(len(results), 150)
        self.assertEqual(results[0]["external_id"], "1")
        self.assertEqual(results[149]["external_id"], "150")

    def test_collect_empty_content(self) -> None:
        payload = {"content": [], "totalFound": 0}
        with patch(
            "jobforager.search.smartrecruiters.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.smartrecruiters.time.sleep"):
                results = collect_smartrecruiters_jobs(company_slugs=["empty"], delay=0)
        self.assertEqual(results, [])

    def test_collect_network_error(self) -> None:
        with patch(
            "jobforager.search.smartrecruiters.urllib.request.urlopen",
            side_effect=IOError("network down"),
        ):
            with patch("jobforager.search.smartrecruiters.time.sleep"):
                results = collect_smartrecruiters_jobs(company_slugs=["fail"], delay=0)
        self.assertEqual(results, [])

    def test_collect_missing_optional_fields(self) -> None:
        payload = {
            "content": [
                {
                    "id": "minimal",
                    "name": "Minimal Job",
                    "postingUrl": "https://example.com/minimal",
                }
            ],
            "totalFound": 1,
        }
        with patch(
            "jobforager.search.smartrecruiters.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.smartrecruiters.time.sleep"):
                results = collect_smartrecruiters_jobs(company_slugs=["minimal"], delay=0)
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["company"], "minimal")
        self.assertIsNone(job["location"])
        self.assertIsNone(job["description"])
        self.assertEqual(job["tags"], [])


if __name__ == "__main__":
    unittest.main()
