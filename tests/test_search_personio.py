from __future__ import annotations

import unittest
from unittest.mock import patch

from jobforager.search.personio import collect_personio_jobs


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


class TestCollectPersonioJobs(unittest.TestCase):
    def _mock_response(self, body: str) -> MockResponse:
        return MockResponse(body.encode("utf-8"))

    def test_collect_returns_jobs(self) -> None:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<workzag-jobs>
  <position>
    <id>123</id>
    <subcompany>TestCo</subcompany>
    <office>Berlin</office>
    <department>Engineering</department>
    <name>Senior Backend Engineer</name>
    <jobDescriptions>
      <jobDescription>
        <name>About the role</name>
        <value><![CDATA[Build APIs.]]></value>
      </jobDescription>
    </jobDescriptions>
    <employmentType>permanent</employmentType>
    <seniority>experienced</seniority>
    <schedule>full-time</schedule>
    <createdAt>2024-01-15T10:00:00+00:00</createdAt>
  </position>
  <position>
    <id>456</id>
    <subcompany>TestCo</subcompany>
    <office>London</office>
    <additionalOffices>
      <office>Remote</office>
    </additionalOffices>
    <department>Security</department>
    <name>Security Engineer</name>
    <jobDescriptions>
      <jobDescription>
        <name>About the role</name>
        <value><![CDATA[Secure systems.]]></value>
      </jobDescription>
    </jobDescriptions>
    <employmentType>permanent</employmentType>
    <seniority>experienced</seniority>
    <schedule>full-time</schedule>
    <createdAt>2024-02-20T14:30:00+00:00</createdAt>
  </position>
</workzag-jobs>
"""
        with patch(
            "jobforager.search.personio.urllib.request.urlopen",
            return_value=self._mock_response(xml),
        ):
            results = collect_personio_jobs(subdomains=["testco"], max_workers=1)

        self.assertEqual(len(results), 2)

        job = results[0]
        self.assertEqual(job["source"], "personio")
        self.assertEqual(job["title"], "Senior Backend Engineer")
        self.assertEqual(job["company"], "TestCo")
        self.assertEqual(job["location"], "Berlin")
        self.assertEqual(job["job_url"], "https://testco.jobs.personio.de/job/123")
        self.assertEqual(job["posted_at"], "2024-01-15T10:00:00+00:00")
        self.assertEqual(job["external_id"], "123")
        self.assertEqual(job["remote_type"], None)
        self.assertIsNone(job["salary_raw"])
        self.assertIn("Build APIs.", job["description"])
        self.assertEqual(job["metadata"]["subdomain"], "testco")
        self.assertEqual(job["metadata"]["department"], "Engineering")

        job2 = results[1]
        self.assertEqual(job2["title"], "Security Engineer")
        self.assertEqual(job2["location"], "London, Remote")
        self.assertEqual(job2["external_id"], "456")

    def test_collect_empty_xml_returns_empty(self) -> None:
        xml = "<?xml version=\"1.0\"?><workzag-jobs></workzag-jobs>"
        with patch(
            "jobforager.search.personio.urllib.request.urlopen",
            return_value=self._mock_response(xml),
        ):
            results = collect_personio_jobs(subdomains=["testco"], max_workers=1)
        self.assertEqual(results, [])

    def test_collect_network_error_returns_empty(self) -> None:
        with patch(
            "jobforager.search.personio.urllib.request.urlopen",
            side_effect=Exception("network error"),
        ):
            results = collect_personio_jobs(subdomains=["testco"], max_workers=1)
        self.assertEqual(results, [])

    def test_collect_malformed_xml_returns_empty(self) -> None:
        with patch(
            "jobforager.search.personio.urllib.request.urlopen",
            return_value=self._mock_response("not xml"),
        ):
            results = collect_personio_jobs(subdomains=["testco"], max_workers=1)
        self.assertEqual(results, [])

    def test_multiple_subdomains(self) -> None:
        xml_a = """<?xml version="1.0"?>
<workzag-jobs>
  <position>
    <id>1</id>
    <subcompany>CoA</subcompany>
    <office>Berlin</office>
    <name>Engineer A</name>
    <createdAt>2024-01-01T00:00:00+00:00</createdAt>
  </position>
</workzag-jobs>
"""
        xml_b = """<?xml version="1.0"?>
<workzag-jobs>
  <position>
    <id>2</id>
    <subcompany>CoB</subcompany>
    <office>London</office>
    <name>Engineer B</name>
    <createdAt>2024-01-02T00:00:00+00:00</createdAt>
  </position>
</workzag-jobs>
"""
        responses = {"a": xml_a, "b": xml_b}

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            subdomain = url.split("//")[1].split(".")[0]
            return self._mock_response(responses[subdomain])

        with patch(
            "jobforager.search.personio.urllib.request.urlopen",
            side_effect=mock_urlopen,
        ):
            results = collect_personio_jobs(subdomains=["a", "b"], max_workers=1)

        self.assertEqual(len(results), 2)
        titles = {j["title"] for j in results}
        self.assertEqual(titles, {"Engineer A", "Engineer B"})


if __name__ == "__main__":
    unittest.main()
