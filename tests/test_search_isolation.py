from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import patch

from jobforager.cli import main


class TestSearchIsolation(unittest.TestCase):
    def test_one_source_fails_other_succeeds(self) -> None:
        import io
        import contextlib

        fake_remotive = [
            {
                "source": "remotive",
                "title": "Python Developer",
                "company": "Acme",
                "job_url": "https://acme.com/jobs/1",
                "location": "Remote",
                "remote_type": "remote",
                "tags": ["python"],
            }
        ]

        def failing_hn():
            raise RuntimeError("HN API error")

        with patch(
            "jobforager.cli.pipeline.collect_remotive_jobs",
            return_value=fake_remotive,
        ):
            with patch(
                "jobforager.cli.pipeline.collect_hackernews_jobs",
                side_effect=failing_hn,
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
        self.assertIn("Python Developer", rendered)
        self.assertIn("error source=hackernews", rendered)
        self.assertIn("status=completed_with_collector_errors", rendered)

    def test_all_sources_fail(self) -> None:
        import io
        import contextlib

        def failing():
            raise RuntimeError("fail")

        with patch(
            "jobforager.cli.pipeline.collect_remotive_jobs",
            side_effect=failing,
        ):
            with patch(
                "jobforager.cli.pipeline.collect_hackernews_jobs",
                side_effect=failing,
            ):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exit_code = main(
                        ["search", "--sources", "remotive,hackernews"]
                    )
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("error source=remotive", rendered)
        self.assertIn("error source=hackernews", rendered)
        self.assertIn("status=completed_with_collector_errors", rendered)


if __name__ == "__main__":
    unittest.main()
