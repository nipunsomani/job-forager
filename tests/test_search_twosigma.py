from __future__ import annotations

import unittest
from unittest.mock import patch

from jobforager.search.twosigma import collect_twosigma_jobs


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


class TestCollectTwosigmaJobs(unittest.TestCase):
    def _mock_response(self, body: str) -> MockResponse:
        return MockResponse(body.encode("utf-8"))

    def test_collect_returns_jobs(self) -> None:
        rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>careers</title>
    <item>
      <title><![CDATA[Quantitative Software Engineer]]></title>
      <description><![CDATA[United States New York City]]></description>
      <guid isPermaLink="true">https://careers.twosigma.com/careers/JobDetail/New-York-City-United-States-Quantitative-Software-Engineer/13045</guid>
      <link>https://careers.twosigma.com/careers/JobDetail/New-York-City-United-States-Quantitative-Software-Engineer/13045</link>
      <pubDate>Wed, 12 Mar 2025 00:00:00 +0000</pubDate>
    </item>
    <item>
      <title><![CDATA[Reliability Engineer]]></title>
      <description><![CDATA[United Kingdom of Great Britain and Northern Ireland London]]></description>
      <guid isPermaLink="true">https://careers.twosigma.com/careers/JobDetail/London-United-Kingdom-of-Great-Britain-and-Northern-Ireland-Reliability-Engineer/13072</guid>
      <link>https://careers.twosigma.com/careers/JobDetail/London-United-Kingdom-of-Great-Britain-and-Northern-Ireland-Reliability-Engineer/13072</link>
      <pubDate>Fri, 28 Mar 2025 00:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""
        with patch(
            "jobforager.search.twosigma.urllib.request.urlopen",
            return_value=self._mock_response(rss),
        ):
            results = collect_twosigma_jobs()
        self.assertEqual(len(results), 2)

        job = results[0]
        self.assertEqual(job["source"], "twosigma")
        self.assertEqual(job["title"], "Quantitative Software Engineer")
        self.assertEqual(job["company"], "Two Sigma")
        self.assertEqual(
            job["job_url"],
            "https://careers.twosigma.com/careers/JobDetail/New-York-City-United-States-Quantitative-Software-Engineer/13045",
        )
        self.assertEqual(job["location"], "United States New York City")
        self.assertEqual(job["posted_at"], "2025-03-12T00:00:00+0000")
        self.assertEqual(job["external_id"], "13045")
        self.assertIsNone(job["remote_type"])
        self.assertIsNone(job["salary_raw"])
        self.assertIsNone(job["description"])
        self.assertEqual(job["tags"], [])
        self.assertEqual(job["metadata"], {})

        job2 = results[1]
        self.assertEqual(job2["title"], "Reliability Engineer")
        self.assertEqual(job2["external_id"], "13072")

    def test_collect_empty_rss_returns_empty(self) -> None:
        rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>careers</title>
  </channel>
</rss>
"""
        with patch(
            "jobforager.search.twosigma.urllib.request.urlopen",
            return_value=self._mock_response(rss),
        ):
            results = collect_twosigma_jobs()
        self.assertEqual(results, [])

    def test_collect_network_error_returns_empty(self) -> None:
        with patch(
            "jobforager.search.twosigma.urllib.request.urlopen",
            side_effect=Exception("network error"),
        ):
            results = collect_twosigma_jobs()
        self.assertEqual(results, [])

    def test_collect_malformed_xml_returns_empty(self) -> None:
        with patch(
            "jobforager.search.twosigma.urllib.request.urlopen",
            return_value=self._mock_response("not xml"),
        ):
            results = collect_twosigma_jobs()
        self.assertEqual(results, [])

    def test_strip_cdata_without_wrapper(self) -> None:
        from jobforager.search.twosigma import _strip_cdata
        self.assertEqual(_strip_cdata("Engineer"), "Engineer")
        self.assertEqual(_strip_cdata("  Engineer  "), "Engineer")
        self.assertIsNone(_strip_cdata(""))
        self.assertIsNone(_strip_cdata(None))

    def test_parse_rfc822_date_valid(self) -> None:
        from jobforager.search.twosigma import _parse_rfc822_date
        self.assertEqual(
            _parse_rfc822_date("Wed, 12 Mar 2025 00:00:00 +0000"),
            "2025-03-12T00:00:00+0000",
        )

    def test_parse_rfc822_date_invalid(self) -> None:
        from jobforager.search.twosigma import _parse_rfc822_date
        self.assertIsNone(_parse_rfc822_date("not a date"))
        self.assertIsNone(_parse_rfc822_date(""))


if __name__ == "__main__":
    unittest.main()
