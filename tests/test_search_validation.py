from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from jobforager.search.validation import validate_job_url, validate_job_urls


class MockResponse:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class TestValidation(unittest.TestCase):
    def test_validate_job_url_ok(self) -> None:
        with patch(
            "jobforager.search.validation.urllib.request.urlopen",
            return_value=MockResponse(200),
        ):
            result = validate_job_url("https://example.com/jobs/1")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["http_code"], 200)

    def test_validate_job_url_404(self) -> None:
        import urllib.error

        def raise_404(*args, **kwargs):
            raise urllib.error.HTTPError(
                url="https://example.com/jobs/1",
                code=404,
                msg="Not Found",
                hdrs={},
                fp=io.BytesIO(b""),
            )

        with patch(
            "jobforager.search.validation.urllib.request.urlopen",
            side_effect=raise_404,
        ):
            result = validate_job_url("https://example.com/jobs/1")
        self.assertEqual(result["status"], "unreachable")
        self.assertEqual(result["http_code"], 404)

    def test_validate_job_url_timeout(self) -> None:
        with patch(
            "jobforager.search.validation.urllib.request.urlopen",
            side_effect=TimeoutError,
        ):
            result = validate_job_url("https://example.com/jobs/1")
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["http_code"])
        self.assertIn("timed out", result["message"].lower())

    def test_validate_job_url_405_fallback_to_get(self) -> None:
        import urllib.error

        class _FakeReq:
            def __init__(self, url, method=None, **kw):
                self.full_url = url
                self.method = method or "GET"
            def add_header(self, *args):
                pass
            def get_method(self):
                return self.method

        call_count = 0
        def side_effect(req, **kwargs):
            nonlocal call_count
            call_count += 1
            method = getattr(req, "method", None) or getattr(req, "get_method", lambda: "GET")()
            if method == "HEAD":
                raise urllib.error.HTTPError(
                    url="https://example.com/jobs/1",
                    code=405,
                    msg="Method Not Allowed",
                    hdrs={},
                    fp=io.BytesIO(b""),
                )
            return MockResponse(200)

        with patch(
            "jobforager.search.validation.urllib.request.Request",
            side_effect=lambda url, method=None, **kw: _FakeReq(url, method),
        ):
            with patch(
                "jobforager.search.validation.urllib.request.urlopen",
                side_effect=side_effect,
            ):
                result = validate_job_url("https://example.com/jobs/1")
        self.assertEqual(result["status"], "ok")

    def test_validate_job_urls_batch(self) -> None:
        with patch(
            "jobforager.search.validation.urllib.request.urlopen",
            return_value=MockResponse(200),
        ):
            from jobforager.models import JobRecord

            jobs = [
                JobRecord(source="a", title="t", company="c", job_url="https://a.com"),
                JobRecord(source="b", title="t", company="c", job_url="https://b.com"),
            ]
            results = validate_job_urls(jobs)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["status"], "ok")
        self.assertEqual(results[1]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
