from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from jobforager.search.hackernews import (
    collect_hackernews_jobs,
    fetch_hn_item,
    find_hn_whos_hiring_thread,
    parse_hn_job_comment,
)


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


class TestFindHnThread(unittest.TestCase):
    def test_find_thread_success(self) -> None:
        payload = {
            "hits": [
                {"objectID": "12345"}
            ]
        }
        with patch(
            "jobforager.search.hackernews.urllib.request.urlopen",
            return_value=MockResponse(json.dumps(payload).encode("utf-8")),
        ):
            result = find_hn_whos_hiring_thread(2024, 1)
        self.assertEqual(result, 12345)

    def test_find_thread_no_hits(self) -> None:
        payload = {"hits": []}
        with patch(
            "jobforager.search.hackernews.urllib.request.urlopen",
            return_value=MockResponse(json.dumps(payload).encode("utf-8")),
        ):
            result = find_hn_whos_hiring_thread(2024, 1)
        self.assertIsNone(result)

    def test_find_thread_network_error(self) -> None:
        with patch(
            "jobforager.search.hackernews.urllib.request.urlopen",
            side_effect=IOError("fail"),
        ):
            result = find_hn_whos_hiring_thread(2024, 1)
        self.assertIsNone(result)


class TestFetchHnItem(unittest.TestCase):
    def test_fetch_success(self) -> None:
        payload = {"id": 1, "title": "Test"}
        with patch(
            "jobforager.search.hackernews.urllib.request.urlopen",
            return_value=MockResponse(json.dumps(payload).encode("utf-8")),
        ):
            result = fetch_hn_item(1)
        self.assertEqual(result, payload)

    def test_fetch_failure(self) -> None:
        with patch(
            "jobforager.search.hackernews.urllib.request.urlopen",
            side_effect=IOError("fail"),
        ):
            result = fetch_hn_item(1)
        self.assertIsNone(result)


class TestParseHnJobComment(unittest.TestCase):
    def test_parse_pipe_delimited(self) -> None:
        comment = {
            "id": 999,
            "text": "Acme | Python Dev | Remote | yes | $100k-$150k\nBuild APIs. Apply: https://acme.com/jobs/1",
            "time": 1705276800,
            "parent": 1000,
            "by": "user1",
        }
        result = parse_hn_job_comment(comment)
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "hackernews")
        self.assertEqual(result["title"], "Python Dev")
        self.assertEqual(result["company"], "Acme")
        self.assertEqual(result["location"], "Remote")
        self.assertEqual(result["remote_type"], "remote")
        self.assertEqual(result["salary_raw"], "$100k-$150k")
        self.assertEqual(result["job_url"], "https://acme.com/jobs/1")
        self.assertEqual(result["apply_url"], "https://acme.com/jobs/1")
        self.assertEqual(result["external_id"], "999")
        self.assertEqual(result["tags"], ["hackernews"])
        self.assertIn("Build APIs.", result["description"])
        self.assertIsNotNone(result["posted_at"])

    def test_parse_no_text(self) -> None:
        comment = {"id": 1}
        result = parse_hn_job_comment(comment)
        self.assertIsNone(result)

    def test_parse_empty_text(self) -> None:
        comment = {"id": 1, "text": "   "}
        result = parse_hn_job_comment(comment)
        self.assertIsNone(result)

    def test_parse_fallback_no_pipe(self) -> None:
        comment = {
            "id": 2,
            "text": "We are hiring a Go developer at Beta. https://beta.com/jobs",
            "time": 1705276800,
        }
        result = parse_hn_job_comment(comment)
        self.assertIsNotNone(result)
        self.assertEqual(result["company"], "Unknown Company")
        self.assertEqual(result["title"], "We are hiring a Go developer at Beta. https://beta.com/jobs")
        self.assertEqual(result["job_url"], "https://beta.com/jobs")

    def test_parse_remote_mappings(self) -> None:
        for raw, expected in [
            ("yes", "remote"),
            ("remote", "remote"),
            ("no", "onsite"),
            ("hybrid", "hybrid"),
            ("maybe", None),
        ]:
            comment = {
                "id": 3,
                "text": f"Co | Role | Loc | {raw} | $100k<br>Desc.",
                "time": 1705276800,
            }
            result = parse_hn_job_comment(comment)
            self.assertEqual(result["remote_type"], expected, f"failed for {raw}")


class TestCollectHackernewsJobs(unittest.TestCase):
    def test_collect_success(self) -> None:
        thread_payload = {"kids": [1001, 1002]}
        comment_1 = {
            "id": 1001,
            "text": "Acme | Python Dev | Remote | yes | $100k\nBuild APIs. https://acme.com/jobs/1",
            "time": 1705276800,
            "parent": 12345,
            "by": "user1",
        }
        comment_2 = {
            "id": 1002,
            "text": "   ",
            "time": 1705276800,
        }

        call_count = 0
        def mock_urlopen(req, **kwargs):
            nonlocal call_count
            call_count += 1
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            if "algolia" in url:
                return MockResponse(
                    json.dumps({"hits": [{"objectID": "12345"}]}).encode("utf-8")
                )
            if "item/12345" in url:
                return MockResponse(json.dumps(thread_payload).encode("utf-8"))
            if "item/1001" in url:
                return MockResponse(json.dumps(comment_1).encode("utf-8"))
            if "item/1002" in url:
                return MockResponse(json.dumps(comment_2).encode("utf-8"))
            return MockResponse(b"{}")

        with patch(
            "jobforager.search.hackernews.urllib.request.urlopen",
            side_effect=mock_urlopen,
        ):
            with patch("jobforager.search.hackernews.time.sleep"):
                results = collect_hackernews_jobs(year=2024, month=1, max_comments=2, delay=0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Python Dev")

    def test_collect_no_thread(self) -> None:
        with patch(
            "jobforager.search.hackernews.urllib.request.urlopen",
            return_value=MockResponse(json.dumps({"hits": []}).encode("utf-8")),
        ):
            results = collect_hackernews_jobs(year=2024, month=1)
        self.assertEqual(results, [])

    def test_collect_exception_handling(self) -> None:
        with patch(
            "jobforager.search.hackernews.find_hn_whos_hiring_thread",
            side_effect=RuntimeError("boom"),
        ):
            results = collect_hackernews_jobs(year=2024, month=1)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
