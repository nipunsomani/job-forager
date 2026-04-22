import json
import unittest
from unittest.mock import patch

from jobforager.search.hiringcafe import (
    _normalize_job,
    _strip_html,
    collect_hiringcafe_jobs,
)


class TestStripHtml(unittest.TestCase):
    def test_removes_tags(self) -> None:
        self.assertEqual(_strip_html("<p>Hello</p>"), "Hello")

    def test_removes_script(self) -> None:
        self.assertEqual(
            _strip_html("<script>alert(1)</script>Text"),
            "Text",
        )

    def test_removes_style(self) -> None:
        self.assertEqual(
            _strip_html("<style>.x{}</style>Text"),
            "Text",
        )

    def test_empty(self) -> None:
        self.assertEqual(_strip_html(""), "")


class TestNormalizeJob(unittest.TestCase):
    def test_valid_job(self) -> None:
        job = {
            "id": "123",
            "source": "TechCorp",
            "apply_url": "https://example.com/job",
            "board_token": "techcorp",
            "source_and_board_token": "techcorp_board",
            "job_information": {
                "title": "Software Engineer",
                "description": "<p>Build things</p>",
                "viewedByUsers": ["u1"],
                "appliedFromUsers": [],
                "savedFromUsers": ["u2"],
                "hiddenFromUsers": [],
            },
        }
        result = _normalize_job(job)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["title"], "Software Engineer")
        self.assertEqual(result["company"], "TechCorp")
        self.assertEqual(result["job_url"], "https://example.com/job")
        self.assertEqual(result["description"], "Build things")
        self.assertEqual(result["source"], "hiringcafe")
        self.assertEqual(result["metadata"]["viewed_count"], 1)
        self.assertEqual(result["metadata"]["saved_count"], 1)

    def test_missing_title(self) -> None:
        job = {
            "id": "123",
            "source": "TechCorp",
            "apply_url": "https://example.com/job",
            "job_information": {"title": "", "description": ""},
        }
        self.assertIsNone(_normalize_job(job))

    def test_missing_company(self) -> None:
        job = {
            "id": "123",
            "source": "",
            "apply_url": "https://example.com/job",
            "job_information": {"title": "Engineer", "description": ""},
        }
        self.assertIsNone(_normalize_job(job))


class TestCollectHiringcafeJobs(unittest.TestCase):
    @patch("jobforager.search.hiringcafe._fetch_total_count")
    @patch("jobforager.search.hiringcafe._fetch_jobs_page")
    def test_collects_jobs(self, mock_fetch_page, mock_count) -> None:
        mock_count.return_value = 2
        mock_fetch_page.return_value = [
            {
                "id": "1",
                "source": "CorpA",
                "apply_url": "https://a.com/1",
                "job_information": {
                    "title": "Engineer",
                    "description": "<p>Do work</p>",
                    "viewedByUsers": [],
                    "appliedFromUsers": [],
                    "savedFromUsers": [],
                    "hiddenFromUsers": [],
                },
            },
            {
                "id": "2",
                "source": "CorpB",
                "apply_url": "https://b.com/2",
                "job_information": {
                    "title": "Designer",
                    "description": "<p>Design things</p>",
                    "viewedByUsers": [],
                    "appliedFromUsers": [],
                    "savedFromUsers": [],
                    "hiddenFromUsers": [],
                },
            },
        ]

        jobs = collect_hiringcafe_jobs(search_query="python", max_results=2)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["title"], "Engineer")
        self.assertEqual(jobs[1]["title"], "Designer")

    @patch("jobforager.search.hiringcafe._fetch_total_count")
    def test_zero_count_returns_empty(self, mock_count) -> None:
        mock_count.return_value = 0
        jobs = collect_hiringcafe_jobs()
        self.assertEqual(jobs, [])

    @patch("jobforager.search.hiringcafe._fetch_total_count")
    @patch("jobforager.search.hiringcafe._fetch_jobs_page")
    def test_respects_max_results(self, mock_fetch_page, mock_count) -> None:
        mock_count.return_value = 100
        mock_fetch_page.return_value = [
            {
                "id": str(i),
                "source": "Corp",
                "apply_url": f"https://corp.com/{i}",
                "job_information": {
                    "title": f"Job {i}",
                    "description": "",
                    "viewedByUsers": [],
                    "appliedFromUsers": [],
                    "savedFromUsers": [],
                    "hiddenFromUsers": [],
                },
            }
            for i in range(10)
        ]

        jobs = collect_hiringcafe_jobs(max_results=5)
        self.assertEqual(len(jobs), 5)


if __name__ == "__main__":
    unittest.main()
