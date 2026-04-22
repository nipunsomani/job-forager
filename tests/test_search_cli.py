from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import patch

from jobforager.cli import main


class TestSearchCli(unittest.TestCase):
    def test_search_help(self) -> None:
        import io
        import contextlib

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                exit_code = main(["search", "--help"])
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 0
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("--keywords", rendered)
        self.assertIn("--location", rendered)
        self.assertIn("--since", rendered)
        self.assertIn("--last", rendered)
        self.assertIn("--sources", rendered)
        self.assertIn("--profile", rendered)

    def test_search_invalid_since_format(self) -> None:
        import io
        import contextlib

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(["search", "--since", "not-a-date"])
        self.assertEqual(exit_code, 1)
        self.assertIn("search error:", output.getvalue())

    def test_search_invalid_last_format(self) -> None:
        import io
        import contextlib

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(["search", "--last", "not-valid"])
        self.assertEqual(exit_code, 1)
        self.assertIn("search error:", output.getvalue())

    def test_search_smoke_with_mocked_sources(self) -> None:
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
                "description": "Build APIs.",
            }
        ]
        fake_hn = [
            {
                "source": "hackernews",
                "title": "Rust Developer",
                "company": "Beta",
                "job_url": "https://beta.com/jobs/2",
                "location": "Remote",
                "remote_type": "remote",
                "tags": ["hackernews"],
                "description": "Build systems.",
            }
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
                    "jobforager.cli.pipeline.validate_job_urls",
                    return_value=[
                        {"status": "ok", "http_code": 200},
                        {"status": "ok", "http_code": 200},
                    ],
                ):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        exit_code = main(
                            [
                                "search",
                                "--keywords",
                                "developer",
                                "--sources",
                                "remotive,hackernews",
                            ]
                        )
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("job-forager search", rendered)
        self.assertIn("sources_queried=remotive,hackernews", rendered)
        self.assertIn("fetched=2", rendered)
        self.assertIn("matched=2", rendered)
        self.assertIn("Python Developer", rendered)
        self.assertIn("Rust Developer", rendered)
        self.assertIn("status=completed_clean", rendered)

    def test_search_keyword_filtering(self) -> None:
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
            },
            {
                "source": "remotive",
                "title": "Java Developer",
                "company": "Beta",
                "job_url": "https://beta.com/jobs/2",
                "location": "Remote",
                "remote_type": "remote",
                "tags": ["java"],
            },
        ]

        with patch(
            "jobforager.cli.pipeline.collect_remotive_jobs",
            return_value=fake_remotive,
        ):
            with patch(
                "jobforager.cli.pipeline.collect_hackernews_jobs",
                return_value=[],
            ):
                with patch(
                    "jobforager.cli.pipeline.validate_job_urls",
                    return_value=[
                        {"status": "ok", "http_code": 200},
                    ],
                ):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        exit_code = main(
                            [
                                "search",
                                "--keywords",
                                "python",
                                "--sources",
                                "remotive",
                            ]
                        )
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Python Developer", rendered)
        self.assertNotIn("Java Developer", rendered)

    def test_search_per_source_failure_isolation(self) -> None:
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
            raise RuntimeError("HN API down")

        with patch(
            "jobforager.cli.pipeline.collect_remotive_jobs",
            return_value=fake_remotive,
        ):
            with patch(
                "jobforager.cli.pipeline.collect_hackernews_jobs",
                side_effect=failing_hn,
            ):
                with patch(
                    "jobforager.cli.pipeline.validate_job_urls",
                    return_value=[{"status": "ok", "http_code": 200}],
                ):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        exit_code = main(
                            [
                                "search",
                                "--sources",
                                "remotive,hackernews",
                            ]
                        )
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Python Developer", rendered)
        self.assertIn("error source=hackernews", rendered)
        self.assertIn("status=completed_with_collector_errors", rendered)

    def test_search_with_profile(self) -> None:
        import io
        import contextlib
        from pathlib import Path

        profile_path = (
            Path(__file__).resolve().parents[1]
            / "config"
            / "profile.example.toml"
        )

        fake_remotive = [
            {
                "source": "remotive",
                "title": "Senior Software Engineer",
                "company": "Acme",
                "job_url": "https://acme.com/jobs/1",
                "location": "City, Country",
                "remote_type": "remote",
                "tags": ["python", "fastapi"],
                "salary_max_usd": 150000,
            },
            {
                "source": "remotive",
                "title": "Junior Engineer",
                "company": "Beta",
                "job_url": "https://beta.com/jobs/2",
                "location": "City, Country",
                "remote_type": "remote",
                "tags": ["python"],
                "salary_max_usd": 50000,
            },
        ]

        with patch(
            "jobforager.cli.pipeline.collect_remotive_jobs",
            return_value=fake_remotive,
        ):
            with patch(
                "jobforager.cli.pipeline.collect_hackernews_jobs",
                return_value=[],
            ):
                with patch(
                    "jobforager.cli.pipeline.validate_job_urls",
                    return_value=[
                        {"status": "ok", "http_code": 200},
                    ],
                ):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        exit_code = main(
                            [
                                "search",
                                "--profile",
                                str(profile_path),
                                "--sources",
                                "remotive",
                            ]
                        )
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Senior Software Engineer", rendered)
        self.assertNotIn("Junior Engineer", rendered)


if __name__ == "__main__":
    unittest.main()
