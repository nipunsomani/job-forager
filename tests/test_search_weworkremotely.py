from __future__ import annotations

import unittest
from unittest.mock import patch

from jobforager.search.weworkremotely import collect_weworkremotely_jobs


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


RSS_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>We Work Remotely</title>
    <item>
      <title>Acme Inc: Python Developer</title>
      <link>https://weworkremotely.com/remote-jobs/acme-inc-python-developer</link>
      <pubDate>Mon, 15 Jan 2024 00:00:00 GMT</pubDate>
      <description><![CDATA[Build Python APIs.]]></description>
      <category>Programming</category>
      <category>Backend</category>
    </item>
    <item>
      <title>DevOps Engineer</title>
      <link>https://weworkremotely.com/remote-jobs/devops-engineer</link>
      <pubDate>Tue, 16 Jan 2024 00:00:00 GMT</pubDate>
      <description><![CDATA[Manage infrastructure.]]></description>
    </item>
  </channel>
</rss>
"""


class TestCollectWeWorkRemotelyJobs(unittest.TestCase):
    def test_collect_returns_jobs(self) -> None:
        with patch(
            "jobforager.search.weworkremotely.urllib.request.urlopen",
            return_value=MockResponse(RSS_FEED),
        ):
            results = collect_weworkremotely_jobs()
        self.assertEqual(len(results), 2)

        job0 = results[0]
        self.assertEqual(job0["source"], "weworkremotely")
        self.assertEqual(job0["title"], "Python Developer")
        self.assertEqual(job0["company"], "Acme Inc")
        self.assertEqual(job0["job_url"], "https://weworkremotely.com/remote-jobs/acme-inc-python-developer")
        self.assertIsNone(job0["location"])
        self.assertEqual(job0["remote_type"], "remote")
        self.assertIsNone(job0["salary_raw"])
        self.assertIsNone(job0["salary_min_usd"])
        self.assertIsNone(job0["salary_max_usd"])
        self.assertEqual(job0["posted_at"], "Mon, 15 Jan 2024 00:00:00 GMT")
        self.assertIsNone(job0["apply_url"])
        self.assertIsNone(job0["external_id"])
        self.assertEqual(job0["description"], "Build Python APIs.")
        self.assertEqual(job0["tags"], ["Programming", "Backend"])
        self.assertEqual(job0["metadata"], {})

        job1 = results[1]
        self.assertEqual(job1["title"], "DevOps Engineer")
        self.assertIsNone(job1["company"])
        self.assertEqual(job1["job_url"], "https://weworkremotely.com/remote-jobs/devops-engineer")
        self.assertEqual(job1["tags"], [])

    def test_collect_empty_feed(self) -> None:
        empty_feed = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>We Work Remotely</title>
  </channel>
</rss>
"""
        with patch(
            "jobforager.search.weworkremotely.urllib.request.urlopen",
            return_value=MockResponse(empty_feed),
        ):
            results = collect_weworkremotely_jobs()
        self.assertEqual(results, [])

    def test_collect_network_error(self) -> None:
        with patch(
            "jobforager.search.weworkremotely.urllib.request.urlopen",
            side_effect=IOError("network down"),
        ):
            results = collect_weworkremotely_jobs()
        self.assertEqual(results, [])

    def test_collect_invalid_xml(self) -> None:
        with patch(
            "jobforager.search.weworkremotely.urllib.request.urlopen",
            return_value=MockResponse(b"not xml"),
        ):
            results = collect_weworkremotely_jobs()
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
