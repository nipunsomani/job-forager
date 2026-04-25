from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from jobforager.search.adzuna import collect_adzuna_jobs


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


class TestCollectAdzunaJobs(unittest.TestCase):
    def setUp(self) -> None:
        self._old_app_id = os.environ.get("ADZUNA_APP_ID")
        self._old_app_key = os.environ.get("ADZUNA_APP_KEY")
        os.environ["ADZUNA_APP_ID"] = "test_id"
        os.environ["ADZUNA_APP_KEY"] = "test_key"

    def tearDown(self) -> None:
        if self._old_app_id is not None:
            os.environ["ADZUNA_APP_ID"] = self._old_app_id
        else:
            os.environ.pop("ADZUNA_APP_ID", None)
        if self._old_app_key is not None:
            os.environ["ADZUNA_APP_KEY"] = self._old_app_key
        else:
            os.environ.pop("ADZUNA_APP_KEY", None)

    def _mock_response(self, payload: dict) -> MockResponse:
        return MockResponse(json.dumps(payload).encode("utf-8"))

    def test_collect_returns_jobs(self) -> None:
        payload = {
            "results": [
                {
                    "job": {
                        "id": "abc123",
                        "title": "  Python Developer  ",
                        "company": {"display_name": "  Acme Inc  "},
                        "location": {"display_name": "  London, UK  "},
                        "redirect_url": "https://www.adzuna.com/jobs/details/abc123",
                        "description": "Build Python APIs.",
                        "created": "2024-01-15T00:00:00Z",
                        "salary_min": 50000,
                        "salary_max": 70000,
                        "salary_currency": "USD",
                        "salary_is_predicted": 0,
                        "contract_type": "permanent",
                        "contract_time": "full_time",
                        "category": {"label": "IT Jobs"},
                    }
                }
            ]
        }
        with patch(
            "jobforager.search.adzuna.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_adzuna_jobs()
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["source"], "adzuna")
        self.assertEqual(job["title"], "Python Developer")
        self.assertEqual(job["company"], "Acme Inc")
        self.assertEqual(job["job_url"], "https://www.adzuna.com/jobs/details/abc123")
        self.assertEqual(job["location"], "London, UK")
        self.assertIsNone(job["remote_type"])
        self.assertEqual(job["salary_raw"], "50000 - 70000 USD")
        self.assertEqual(job["salary_min_usd"], 50000.0)
        self.assertEqual(job["salary_max_usd"], 70000.0)
        self.assertEqual(job["posted_at"], "2024-01-15T00:00:00Z")
        self.assertEqual(job["apply_url"], "https://www.adzuna.com/jobs/details/abc123")
        self.assertEqual(job["external_id"], "abc123")
        self.assertEqual(job["description"], "Build Python APIs.")
        self.assertEqual(job["tags"], ["IT Jobs"])
        self.assertEqual(
            job["metadata"],
            {
                "contract_type": "permanent",
                "contract_time": "full_time",
                "salary_currency": "USD",
            },
        )

    def test_collect_predicted_salary(self) -> None:
        payload = {
            "results": [
                {
                    "job": {
                        "id": "1",
                        "title": "Dev",
                        "company": {"display_name": "Co"},
                        "location": {"display_name": "Remote"},
                        "redirect_url": "https://example.com",
                        "description": "Desc",
                        "created": "2024-01-01T00:00:00Z",
                        "salary_min": 100000,
                        "salary_max": None,
                        "salary_currency": "USD",
                        "salary_is_predicted": 1,
                        "contract_type": None,
                        "contract_time": None,
                        "category": {},
                    }
                }
            ]
        }
        with patch(
            "jobforager.search.adzuna.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_adzuna_jobs()
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["salary_raw"], "100000 USD (predicted)")
        self.assertEqual(job["salary_min_usd"], 100000.0)
        self.assertIsNone(job["salary_max_usd"])

    def test_collect_non_usd_currency(self) -> None:
        payload = {
            "results": [
                {
                    "job": {
                        "id": "1",
                        "title": "Dev",
                        "company": {"display_name": "Co"},
                        "location": {"display_name": "London"},
                        "redirect_url": "https://example.com",
                        "description": "Desc",
                        "created": "2024-01-01T00:00:00Z",
                        "salary_min": 40000,
                        "salary_max": 60000,
                        "salary_currency": "GBP",
                        "salary_is_predicted": 0,
                        "category": {},
                    }
                }
            ]
        }
        with patch(
            "jobforager.search.adzuna.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_adzuna_jobs()
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job["salary_raw"], "40000 - 60000 GBP")
        self.assertIsNone(job["salary_min_usd"])
        self.assertIsNone(job["salary_max_usd"])

    def test_collect_empty_results(self) -> None:
        payload = {"results": []}
        with patch(
            "jobforager.search.adzuna.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_adzuna_jobs()
        self.assertEqual(results, [])

    def test_collect_missing_results_key(self) -> None:
        payload = {}
        with patch(
            "jobforager.search.adzuna.urllib.request.urlopen",
            return_value=self._mock_response(payload),
        ):
            results = collect_adzuna_jobs()
        self.assertEqual(results, [])

    def test_collect_network_error(self) -> None:
        with patch(
            "jobforager.search.adzuna.urllib.request.urlopen",
            side_effect=IOError("network down"),
        ):
            results = collect_adzuna_jobs()
        self.assertEqual(results, [])

    def test_collect_missing_credentials(self) -> None:
        os.environ.pop("ADZUNA_APP_ID", None)
        os.environ.pop("ADZUNA_APP_KEY", None)
        results = collect_adzuna_jobs()
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
