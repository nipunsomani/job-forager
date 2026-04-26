from __future__ import annotations

import unittest
from unittest.mock import patch

from jobforager.search.pinpoint import (
    _normalize_posting,
    _strip_html,
    _subdomain_to_company,
    collect_pinpoint_jobs,
)


class TestStripHtml(unittest.TestCase):
    def test_removes_tags(self) -> None:
        self.assertEqual(_strip_html("<p>Hello</p>"), "Hello")

    def test_empty(self) -> None:
        self.assertEqual(_strip_html(""), "")


class TestSubdomainToCompany(unittest.TestCase):
    def test_known_mapping(self) -> None:
        self.assertEqual(_subdomain_to_company("nypl"), "New York Public Library")
        self.assertEqual(_subdomain_to_company("fifa-careers"), "FIFA")
        self.assertEqual(_subdomain_to_company("made-tech"), "Made Tech")

    def test_title_case_fallback(self) -> None:
        self.assertEqual(_subdomain_to_company("hazelcast"), "Hazelcast")

    def test_hyphen_replacement(self) -> None:
        self.assertEqual(_subdomain_to_company("franklin-electric"), "Franklin Electric")


class TestNormalizePosting(unittest.TestCase):
    def test_full_posting(self) -> None:
        posting = {
            "id": "123",
            "title": "Software Engineer",
            "url": "https://example.com/job",
            "path": "/jobs/123",
            "location": {"name": "London, UK"},
            "workplace_type": "remote",
            "compensation_minimum": 80000,
            "compensation_maximum": 120000,
            "compensation_currency": "USD",
            "compensation_frequency": "year",
            "opened_at": "2024-01-15T00:00:00Z",
            "description": "<p>Build things</p>",
            "department": {"name": "Engineering"},
            "employment_type_text": "Full Time",
            "requisition_id": "REQ-001",
        }
        result = _normalize_posting(posting, "example")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["title"], "Software Engineer")
        self.assertEqual(result["company"], "Example")
        self.assertEqual(result["location"], "London, UK")
        self.assertEqual(result["remote_type"], "remote")
        self.assertEqual(result["salary_min_usd"], 80000)
        self.assertEqual(result["salary_max_usd"], 120000)
        self.assertEqual(result["posted_at"], "2024-01-15T00:00:00Z")
        self.assertEqual(result["description"], "Build things")
        self.assertEqual(result["source"], "pinpoint")
        self.assertEqual(result["metadata"]["subdomain"], "example")
        self.assertEqual(result["metadata"]["department"], "Engineering")

    def test_missing_title(self) -> None:
        self.assertIsNone(_normalize_posting({"id": "123"}, "example"))

    def test_no_url_uses_path(self) -> None:
        posting = {
            "id": "123",
            "title": "Engineer",
            "path": "/jobs/123",
        }
        result = _normalize_posting(posting, "example")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["job_url"], "https://example.pinpointhq.com/jobs/123")

    def test_compensation_string(self) -> None:
        posting = {
            "id": "123",
            "title": "Engineer",
            "compensation": "£50,000 - £70,000 / year",
        }
        result = _normalize_posting(posting, "example")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["salary_raw"], "£50,000 - £70,000 / year")


class TestCollectPinpointJobs(unittest.TestCase):
    @patch("jobforager.search.pinpoint._fetch_subdomain")
    def test_collects_from_multiple_subdomains(self, mock_fetch) -> None:
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            return [
                {
                    "id": str(call_count[0]),
                    "title": "Engineer",
                    "url": f"https://example.com/{call_count[0]}",
                    "location": {"name": "London"},
                }
            ]
        mock_fetch.side_effect = side_effect
        jobs = collect_pinpoint_jobs(max_results=2)
        self.assertEqual(len(jobs), 2)
        self.assertTrue(all(j["source"] == "pinpoint" for j in jobs))

    @patch("jobforager.search.pinpoint._fetch_subdomain")
    def test_search_term_filter(self, mock_fetch) -> None:
        mock_fetch.return_value = [
            {"id": "1", "title": "Software Engineer", "url": "https://a.com"},
            {"id": "2", "title": "Sales Rep", "url": "https://b.com"},
        ]
        jobs = collect_pinpoint_jobs(search_term="engineer")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Software Engineer")

    @patch("jobforager.search.pinpoint._fetch_subdomain")
    def test_location_filter(self, mock_fetch) -> None:
        mock_fetch.return_value = [
            {"id": "1", "title": "Engineer", "url": "https://a.com", "location": {"name": "London"}},
            {"id": "2", "title": "Designer", "url": "https://b.com", "location": {"name": "New York"}},
        ]
        jobs = collect_pinpoint_jobs(location="London")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["location"], "London")

    @patch("jobforager.search.pinpoint._fetch_subdomain")
    def test_deduplicates_by_id(self, mock_fetch) -> None:
        mock_fetch.return_value = [
            {"id": "1", "title": "Engineer", "url": "https://a.com"},
            {"id": "1", "title": "Engineer", "url": "https://a.com"},
        ]
        jobs = collect_pinpoint_jobs()
        self.assertEqual(len(jobs), 1)

    @patch("jobforager.search.pinpoint._fetch_subdomain")
    def test_respects_max_results(self, mock_fetch) -> None:
        mock_fetch.return_value = [
            {"id": str(i), "title": f"Job {i}", "url": f"https://a.com/{i}"}
            for i in range(10)
        ]
        jobs = collect_pinpoint_jobs(max_results=3)
        self.assertEqual(len(jobs), 3)


if __name__ == "__main__":
    unittest.main()
