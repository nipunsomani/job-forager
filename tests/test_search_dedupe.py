from __future__ import annotations

import unittest
from unittest.mock import patch

from jobforager.cli import main


class TestSearchDedupe(unittest.TestCase):
    def test_dedupe_across_sources_by_url(self) -> None:
        import io
        import contextlib

        fake_remotive = [
            {
                "source": "remotive",
                "title": "Senior Engineer",
                "company": "Acme",
                "job_url": "https://acme.com/jobs/1",
                "location": "Remote",
                "remote_type": "remote",
                "tags": ["python"],
            },
        ]
        fake_hn = [
            {
                "source": "hackernews",
                "title": "Senior Engineer",
                "company": "Acme",
                "job_url": "https://acme.com/jobs/1",
                "location": "Remote",
                "remote_type": "remote",
                "tags": ["hackernews"],
            },
        ]

        with patch(
            "jobforager.cli.pipeline.collect_remotive_jobs",
            return_value=fake_remotive,
        ):
            with patch(
                "jobforager.cli.pipeline.collect_hackernews_jobs",
                return_value=fake_hn,
            ):
                with patch(
                    "jobforager.cli.pipeline.validate_job_url",
                    return_value={"status": "ok", "http_code": 200},
                ):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        exit_code = main(
                            ["search", "--sources", "remotive,hackernews"]
                        )
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("fetched=2", rendered)
        self.assertIn("matched=1", rendered)
        self.assertIn("duplicates=1", rendered)

    def test_dedupe_by_external_id(self) -> None:
        from jobforager.models import JobRecord
        from jobforager.normalize import build_dedupe_key

        jobs = [
            JobRecord(
                source="remotive",
                title="Role A",
                company="Co A",
                job_url="https://a.com",
                external_id="abc-123",
            ),
            JobRecord(
                source="remotive",
                title="Role B",
                company="Co B",
                job_url="https://b.com",
                external_id="abc-123",
            ),
        ]
        keys = [build_dedupe_key(job) for job in jobs]
        self.assertEqual(keys[0], keys[1])
        self.assertEqual(len(set(keys)), 1)

    def test_different_jobs_different_keys(self) -> None:
        from jobforager.models import JobRecord
        from jobforager.normalize import build_dedupe_key

        jobs = [
            JobRecord(
                source="remotive",
                title="Role A",
                company="Co A",
                job_url="https://a.com",
            ),
            JobRecord(
                source="hackernews",
                title="Role B",
                company="Co B",
                job_url="https://b.com",
            ),
        ]
        keys = [build_dedupe_key(job) for job in jobs]
        self.assertEqual(len(set(keys)), 2)


if __name__ == "__main__":
    unittest.main()
