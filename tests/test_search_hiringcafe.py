from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from jobforager.search.hiringcafe import (
    _discover_build_id_from_404,
    _extract_company_name,
    _extract_location,
    _extract_remote_type,
    _extract_salary,
    _normalize_job,
    _resolve_location,
    _shard_search_term,
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


class TestExtractCompanyName(unittest.TestCase):
    def test_v5_company_name(self) -> None:
        job = {"v5_processed_job_data": {"company_name": "  Acme  "}}
        self.assertEqual(_extract_company_name(job), "Acme")

    def test_enriched_company_name(self) -> None:
        job = {"enriched_company_data": {"name": "Acme"}}
        self.assertEqual(_extract_company_name(job), "Acme")

    def test_board_token_fallback(self) -> None:
        job = {"board_token": "acme-corp"}
        self.assertEqual(_extract_company_name(job), "acme-corp")

    def test_missing(self) -> None:
        self.assertIsNone(_extract_company_name({}))


class TestExtractLocation(unittest.TestCase):
    def test_v5_location(self) -> None:
        job = {"v5_processed_job_data": {"formatted_workplace_location": "London, UK"}}
        self.assertEqual(_extract_location(job), "London, UK")

    def test_missing(self) -> None:
        self.assertIsNone(_extract_location({}))


class TestExtractRemoteType(unittest.TestCase):
    def test_remote(self) -> None:
        job = {"v5_processed_job_data": {"workplace_type": "Remote"}}
        self.assertEqual(_extract_remote_type(job), "remote")

    def test_hybrid(self) -> None:
        job = {"v5_processed_job_data": {"workplace_type": "hybrid"}}
        self.assertEqual(_extract_remote_type(job), "hybrid")

    def test_onsite(self) -> None:
        job = {"v5_processed_job_data": {"workplace_type": "ONSITE"}}
        self.assertEqual(_extract_remote_type(job), "onsite")

    def test_missing(self) -> None:
        self.assertIsNone(_extract_remote_type({}))


class TestExtractSalary(unittest.TestCase):
    def test_yearly_usd(self) -> None:
        job = {
            "v5_processed_job_data": {
                "yearly_min_compensation": 80000,
                "yearly_max_compensation": 120000,
                "listed_compensation_currency": "USD",
                "listed_compensation_frequency": "yearly",
            }
        }
        raw, min_usd, max_usd = _extract_salary(job)
        self.assertIn("80000", raw or "")
        self.assertIn("120000", raw or "")
        self.assertEqual(min_usd, 80000)
        self.assertEqual(max_usd, 120000)

    def test_monthly_non_usd(self) -> None:
        job = {
            "v5_processed_job_data": {
                "monthly_min_compensation": 5000,
                "monthly_max_compensation": 7000,
                "listed_compensation_currency": "GBP",
            }
        }
        raw, min_usd, max_usd = _extract_salary(job)
        self.assertIn("5000", raw or "")
        self.assertIsNone(min_usd)
        self.assertIsNone(max_usd)

    def test_missing(self) -> None:
        raw, min_usd, max_usd = _extract_salary({})
        self.assertIsNone(raw)
        self.assertIsNone(min_usd)
        self.assertIsNone(max_usd)


class TestNormalizeJob(unittest.TestCase):
    def test_valid_job(self) -> None:
        job = {
            "id": "grnhse___acme___123",
            "source": "grnhse",
            "apply_url": "https://boards.greenhouse.io/acme/jobs/123",
            "board_token": "acme",
            "source_and_board_token": "grnhse_acme",
            "job_information": {
                "title": "Software Engineer",
                "description": "<p>Build things</p>",
            },
            "v5_processed_job_data": {
                "company_name": "Acme",
                "formatted_workplace_location": "San Francisco, CA",
                "workplace_type": "Remote",
                "yearly_min_compensation": 120000,
                "yearly_max_compensation": 160000,
                "listed_compensation_currency": "USD",
                "estimated_publish_date": "2024-01-15",
            },
        }
        result = _normalize_job(job)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["title"], "Software Engineer")
        self.assertEqual(result["company"], "Acme")
        self.assertEqual(result["location"], "San Francisco, CA")
        self.assertEqual(result["remote_type"], "remote")
        self.assertEqual(result["salary_min_usd"], 120000)
        self.assertEqual(result["salary_max_usd"], 160000)
        self.assertEqual(result["posted_at"], "2024-01-15")
        self.assertEqual(result["description"], "Build things")
        self.assertEqual(result["source"], "hiringcafe")
        self.assertEqual(
            result["job_url"],
            "https://hiring.cafe/viewjob/grnhse___acme___123",
        )
        self.assertEqual(result["metadata"]["board_token"], "acme")

    def test_missing_title(self) -> None:
        job = {
            "id": "123",
            "apply_url": "https://example.com/job",
            "job_information": {"title": ""},
            "v5_processed_job_data": {"company_name": "Acme"},
        }
        self.assertIsNone(_normalize_job(job))

    def test_missing_company(self) -> None:
        job = {
            "id": "123",
            "apply_url": "https://example.com/job",
            "job_information": {"title": "Engineer"},
        }
        self.assertIsNone(_normalize_job(job))

    def test_missing_apply_url(self) -> None:
        job = {
            "id": "123",
            "apply_url": "",
            "job_information": {"title": "Engineer"},
            "v5_processed_job_data": {"company_name": "Acme"},
        }
        self.assertIsNone(_normalize_job(job))


class TestShardSearchTerm(unittest.TestCase):
    def test_short_query_no_shard(self) -> None:
        self.assertEqual(_shard_search_term("security engineer"), ["security engineer"])

    def test_long_query_shard(self) -> None:
        shards = _shard_search_term("a b c d e f")
        self.assertEqual(len(shards), 2)
        self.assertEqual(shards[0], "a b c")
        self.assertEqual(shards[1], "d e f")

    def test_empty(self) -> None:
        self.assertEqual(_shard_search_term(None), [""])
        self.assertEqual(_shard_search_term(""), [""])


class TestCollectHiringcafeJobs(unittest.TestCase):
    def _make_hit(self, job_id: str, title: str, company: str) -> dict[str, Any]:
        return {
            "id": job_id,
            "source": "grnhse",
            "apply_url": f"https://example.com/{job_id}",
            "board_token": company.lower(),
            "job_information": {"title": title, "description": ""},
            "v5_processed_job_data": {"company_name": company},
        }

    @patch("jobforager.search.hiringcafe._fetch_page")
    def test_collects_jobs(self, mock_fetch) -> None:
        mock_fetch.return_value = [
            self._make_hit("1", "Engineer", "CorpA"),
            self._make_hit("2", "Designer", "CorpB"),
        ]

        jobs = collect_hiringcafe_jobs(search_term="python")
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["title"], "Engineer")
        self.assertEqual(jobs[1]["title"], "Designer")

    @patch("jobforager.search.hiringcafe._fetch_page")
    def test_empty_hits_returns_empty(self, mock_fetch) -> None:
        mock_fetch.return_value = []
        jobs = collect_hiringcafe_jobs()
        self.assertEqual(jobs, [])

    @patch("jobforager.search.hiringcafe._fetch_page")
    def test_respects_max_results(self, mock_fetch) -> None:
        mock_fetch.return_value = [
            self._make_hit(str(i), f"Job {i}", "Corp") for i in range(10)
        ]
        jobs = collect_hiringcafe_jobs(max_results=5)
        self.assertEqual(len(jobs), 5)

    @patch("jobforager.search.hiringcafe._fetch_page")
    def test_deduplicates_by_id(self, mock_fetch) -> None:
        # Same ID appears twice
        mock_fetch.return_value = [
            self._make_hit("1", "Engineer", "CorpA"),
            self._make_hit("1", "Engineer", "CorpA"),
        ]
        jobs = collect_hiringcafe_jobs()
        self.assertEqual(len(jobs), 1)

    @patch("jobforager.search.hiringcafe._fetch_page")
    def test_shards_long_query(self, mock_fetch) -> None:
        mock_fetch.return_value = []
        collect_hiringcafe_jobs(search_term="a b c d e f")
        self.assertEqual(mock_fetch.call_count, 2)


class TestDiscoverBuildIdFrom404(unittest.TestCase):
    def test_extracts_from_json_body(self) -> None:
        body = b'{"buildId":"abc123"}'
        self.assertEqual(_discover_build_id_from_404(body), "abc123")

    def test_extracts_from_html_body(self) -> None:
        body = b'<html><script>"buildId":"xyz789"</script></html>'
        self.assertEqual(_discover_build_id_from_404(body), "xyz789")

    def test_none_when_not_found(self) -> None:
        self.assertIsNone(_discover_build_id_from_404(b"no build id here"))

    def test_none_on_bad_encoding(self) -> None:
        self.assertIsNone(_discover_build_id_from_404(b"\xff\xfe"))


class TestResolveLocation(unittest.TestCase):
    @patch("jobforager.search.hiringcafe.urllib.request.urlopen")
    def test_resolves_location(self, mock_urlopen) -> None:
        mock_resp = unittest.mock.Mock()
        mock_resp.read.return_value = json.dumps(
            [
                {
                    "label": "London, England, GB",
                    "value": "xRg1yZQBoEtHp_8UXQ1z",
                    "placeDetail": {
                        "id": "xRg1yZQBoEtHp_8UXQ1z",
                        "formatted_address": "London, England, GB",
                    },
                }
            ]
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__ = lambda s: mock_resp
        mock_urlopen.return_value.__exit__ = lambda *a: None
        result = _resolve_location("london")
        self.assertIsNotNone(result)
        assert result is not None
        # _resolve_location now returns the full wrapper (label+value+placeDetail)
        self.assertEqual(result["label"], "London, England, GB")
        self.assertEqual(result["placeDetail"]["formatted_address"], "London, England, GB")

    @patch("jobforager.search.hiringcafe.urllib.request.urlopen")
    def test_returns_none_on_empty_results(self, mock_urlopen) -> None:
        mock_resp = unittest.mock.Mock()
        mock_resp.read.return_value = b"[]"
        mock_urlopen.return_value.__enter__ = lambda s: mock_resp
        mock_urlopen.return_value.__exit__ = lambda *a: None
        self.assertIsNone(_resolve_location("nowhere"))

    def test_returns_none_for_empty_input(self) -> None:
        self.assertIsNone(_resolve_location(None))
        self.assertIsNone(_resolve_location(""))


if __name__ == "__main__":
    unittest.main()
