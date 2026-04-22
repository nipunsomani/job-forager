from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from jobforager.search.workday import collect_workday_jobs


class MockResponse:
    def __init__(self, body: bytes, status: int = 200, headers: dict | None = None) -> None:
        self._body = body
        self.status = status
        self._headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def info(self):
        class _Info:
            def get_content_charset(self, default="utf-8"):
                return default
        return _Info()

    @property
    def headers(self):
        return self._headers

    def getheader(self, name: str, default=None):
        return self._headers.get(name, default)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class TestCollectWorkdayJobs(unittest.TestCase):
    def _mock_response(self, payload: dict | list, headers: dict | None = None) -> MockResponse:
        return MockResponse(json.dumps(payload).encode("utf-8"), headers=headers)

    def test_collect_returns_jobs(self) -> None:
        csrf_response = MockResponse(b"<html></html>", headers={"x-calypso-csrf-token": "test-csrf-123"})
        jobs_payload = {
            "jobPostings": [
                {
                    "title": "Software Engineer",
                    "externalPath": "/job/Software-Engineer_R123",
                    "postedOn": "2024-01-15T09:00:00Z",
                    "bulletFields": ["R123", "San Francisco, CA"],
                }
            ],
            "total": 1,
        }
        jobs_response = self._mock_response(jobs_payload)

        call_count = 0
        def mock_urlopen(req, **kwargs):
            nonlocal call_count
            call_count += 1
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            if "x-calypso-csrf-token" in (req.headers or {}):
                return csrf_response
            if "/jobs" in url:
                return jobs_response
            return csrf_response

        with patch(
            "jobforager.search.workday.urllib.request.urlopen",
            side_effect=mock_urlopen,
        ):
            with patch("jobforager.search.workday.time.sleep"):
                results = collect_workday_jobs(
                    companies=[{"name": "TestCo", "url": "https://testco.wd5.myworkdayjobs.com/testco"}],
                    delay=0,
                )
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["source"], "workday")
        self.assertEqual(job["title"], "Software Engineer")
        self.assertEqual(job["company"], "TestCo")
        self.assertEqual(
            job["job_url"],
            "https://testco.wd5.myworkdayjobs.com/testco/job/Software-Engineer_R123",
        )
        self.assertEqual(job["location"], "San Francisco, CA")
        self.assertIsNone(job["remote_type"])
        self.assertIsNone(job["salary_raw"])
        self.assertIsNone(job["salary_min_usd"])
        self.assertIsNone(job["salary_max_usd"])
        self.assertEqual(job["posted_at"], "2024-01-15T09:00:00Z")
        self.assertIsNone(job["apply_url"])
        self.assertEqual(job["external_id"], "R123")
        self.assertIsNone(job["description"])
        self.assertEqual(job["tags"], [])
        self.assertEqual(job["metadata"]["career_site_url"], "https://testco.wd5.myworkdayjobs.com/testco")

    def test_collect_pagination(self) -> None:
        csrf_response = MockResponse(b"<html></html>", headers={"x-calypso-csrf-token": "csrf-456"})

        call_count = 0
        def mock_urlopen(req, **kwargs):
            nonlocal call_count
            call_count += 1
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            if "/jobs" not in url:
                return csrf_response
            payload = json.loads(req.data.decode("utf-8")) if hasattr(req, "data") and req.data else {}
            offset = payload.get("offset", 0)
            if offset == 0:
                return MockResponse(
                    json.dumps(
                        {
                            "jobPostings": [
                                {"title": "Job 1", "externalPath": "/j1", "postedOn": "2024-01-01", "bulletFields": ["1"]}
                            ],
                            "total": 2,
                        }
                    ).encode("utf-8")
                )
            if offset == 20:
                return MockResponse(
                    json.dumps(
                        {
                            "jobPostings": [
                                {"title": "Job 2", "externalPath": "/j2", "postedOn": "2024-01-02", "bulletFields": ["2"]}
                            ],
                            "total": 2,
                        }
                    ).encode("utf-8")
                )
            return MockResponse(b'{"jobPostings": [], "total": 2}')

        with patch(
            "jobforager.search.workday.urllib.request.urlopen",
            side_effect=mock_urlopen,
        ):
            with patch("jobforager.search.workday.time.sleep"):
                results = collect_workday_jobs(
                    companies=[{"name": "PagCo", "url": "https://pagco.wd5.myworkdayjobs.com/pagco"}],
                    delay=0,
                )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Job 1")
        self.assertEqual(results[1]["title"], "Job 2")

    def test_collect_no_csrf_token(self) -> None:
        csrf_response = MockResponse(b"<html></html>", headers={})

        with patch(
            "jobforager.search.workday.urllib.request.urlopen",
            return_value=csrf_response,
        ):
            with patch("jobforager.search.workday.time.sleep"):
                results = collect_workday_jobs(
                    companies=[{"name": "NoCsrf", "url": "https://nocsrf.wd5.myworkdayjobs.com/nocsrf"}],
                    delay=0,
                )
        self.assertEqual(results, [])

    def test_collect_empty_jobs(self) -> None:
        csrf_response = MockResponse(b"<html></html>", headers={"x-calypso-csrf-token": "csrf-789"})
        jobs_response = MockResponse(json.dumps({"jobPostings": [], "total": 0}).encode("utf-8"))

        call_count = 0
        def mock_urlopen(req, **kwargs):
            nonlocal call_count
            call_count += 1
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            if "/jobs" in url:
                return jobs_response
            return csrf_response

        with patch(
            "jobforager.search.workday.urllib.request.urlopen",
            side_effect=mock_urlopen,
        ):
            with patch("jobforager.search.workday.time.sleep"):
                results = collect_workday_jobs(
                    companies=[{"name": "EmptyCo", "url": "https://emptyco.wd5.myworkdayjobs.com/emptyco"}],
                    delay=0,
                )
        self.assertEqual(results, [])

    def test_collect_network_error(self) -> None:
        with patch(
            "jobforager.search.workday.urllib.request.urlopen",
            side_effect=IOError("network down"),
        ):
            with patch("jobforager.search.workday.time.sleep"):
                results = collect_workday_jobs(
                    companies=[{"name": "FailCo", "url": "https://failco.wd5.myworkdayjobs.com/failco"}],
                    delay=0,
                )
        self.assertEqual(results, [])

    def test_collect_invalid_url(self) -> None:
        with patch("jobforager.search.workday.time.sleep"):
            results = collect_workday_jobs(
                companies=[{"name": "Bad", "url": "not-a-url"}],
                delay=0,
            )
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
