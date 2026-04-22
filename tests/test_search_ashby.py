from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from jobforager.search.ashby import collect_ashby_jobs


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


class TestCollectAshbyJobs(unittest.TestCase):
    def _mock_response(self, payload: dict) -> MockResponse:
        return MockResponse(json.dumps(payload).encode("utf-8"))

    def test_collect_returns_jobs(self) -> None:
        payload = {
            "jobs": [
                {
                    "title": "Platform Engineer",
                    "location": "San Francisco, CA",
                    "department": "Engineering",
                    "team": "Platform",
                    "isRemote": True,
                    "workplaceType": "Remote",
                    "descriptionPlain": "Build the platform.",
                    "publishedAt": "2024-01-15T12:00:00.000+00:00",
                    "employmentType": "FullTime",
                    "jobUrl": "https://jobs.ashbyhq.com/supabase/1",
                    "applyUrl": "https://jobs.ashbyhq.com/supabase/1/apply",
                }
            ]
        }
        with patch(
            "jobforager.search.ashby.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.ashby.time.sleep"):
                results = collect_ashby_jobs(board_names=["supabase"], delay=0)
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["source"], "ashby")
        self.assertEqual(job["title"], "Platform Engineer")
        self.assertEqual(job["company"], "supabase")
        self.assertEqual(job["job_url"], "https://jobs.ashbyhq.com/supabase/1")
        self.assertEqual(job["location"], "San Francisco, CA")
        self.assertEqual(job["remote_type"], "remote")
        self.assertIsNone(job["salary_raw"])
        self.assertIsNone(job["salary_min_usd"])
        self.assertIsNone(job["salary_max_usd"])
        self.assertEqual(job["posted_at"], "2024-01-15T12:00:00.000+00:00")
        self.assertEqual(job["apply_url"], "https://jobs.ashbyhq.com/supabase/1/apply")
        self.assertIsNone(job["external_id"])
        self.assertEqual(job["description"], "Build the platform.")
        self.assertEqual(sorted(job["tags"]), ["Engineering", "Platform"])
        self.assertEqual(job["metadata"]["board_name"], "supabase")
        self.assertEqual(job["metadata"]["employment_type"], "FullTime")
        self.assertEqual(job["metadata"]["is_remote"], True)

    def test_collect_with_compensation(self) -> None:
        payload = {
            "jobs": [
                {
                    "title": "Product Manager",
                    "location": "Houston, TX",
                    "workplaceType": "Hybrid",
                    "publishedAt": "2024-02-01T10:00:00.000+00:00",
                    "jobUrl": "https://jobs.ashbyhq.com/ramp/2",
                    "compensation": {
                        "compensationTierSummary": "$81K \u2013 $87K \u2022 0.5% \u2013 1.75%",
                        "summaryComponents": [
                            {
                                "compensationType": "Salary",
                                "currencyCode": "USD",
                                "minValue": 81000,
                                "maxValue": 87000,
                            },
                            {
                                "compensationType": "EquityPercentage",
                                "minValue": 0.5,
                                "maxValue": 1.75,
                            },
                        ],
                    },
                }
            ]
        }
        with patch(
            "jobforager.search.ashby.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.ashby.time.sleep"):
                results = collect_ashby_jobs(
                    board_names=["ramp"], include_compensation=True, delay=0
                )
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["salary_raw"], "$81K \u2013 $87K \u2022 0.5% \u2013 1.75%")
        self.assertEqual(job["salary_min_usd"], 81000)
        self.assertEqual(job["salary_max_usd"], 87000)
        self.assertEqual(job["remote_type"], "hybrid")

    def test_collect_empty_jobs(self) -> None:
        payload = {"jobs": []}
        with patch(
            "jobforager.search.ashby.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.ashby.time.sleep"):
                results = collect_ashby_jobs(board_names=["figma"], delay=0)
        self.assertEqual(results, [])

    def test_collect_network_error(self) -> None:
        with patch(
            "jobforager.search.ashby.urllib.request.urlopen",
            side_effect=IOError("network down"),
        ):
            with patch("jobforager.search.ashby.time.sleep"):
                results = collect_ashby_jobs(board_names=["linear"], delay=0)
        self.assertEqual(results, [])

    def test_collect_missing_optional_fields(self) -> None:
        payload = {
            "jobs": [
                {
                    "title": "Designer",
                    "location": "Remote",
                    "workplaceType": "Remote",
                    "publishedAt": "2024-03-01T00:00:00.000+00:00",
                    "jobUrl": "https://jobs.ashbyhq.com/vercel/3",
                }
            ]
        }
        with patch(
            "jobforager.search.ashby.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            with patch("jobforager.search.ashby.time.sleep"):
                results = collect_ashby_jobs(board_names=["vercel"], delay=0)
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertIsNone(job["apply_url"])
        self.assertIsNone(job["description"])
        self.assertEqual(job["tags"], [])


if __name__ == "__main__":
    unittest.main()
