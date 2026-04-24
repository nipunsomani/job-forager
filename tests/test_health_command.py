from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

from jobforager.cli import main


class TestHealthCommand(unittest.TestCase):
    def test_health_all_sources_ok(self) -> None:
        def fake_probe(source: str, timeout: float) -> dict:
            return {"status": "ok", "jobs_found": 1, "elapsed_ms": 100}

        with patch(
            "jobforager.cli.commands.all_sources",
            return_value=["remotive", "hackernews"],
        ):
            with patch(
                "jobforager.cli.commands.run_health_probe",
                side_effect=fake_probe,
            ):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exit_code = main(["health"])

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("source=remotive status=ok", rendered)
        self.assertIn("source=hackernews status=ok", rendered)
        self.assertIn("summary total=2 ok=2 fail=0", rendered)

    def test_health_one_source_fail(self) -> None:
        def fake_probe(source: str, timeout: float) -> dict:
            if source == "remotive":
                return {"status": "ok", "jobs_found": 1, "elapsed_ms": 100}
            return {
                "status": "fail",
                "jobs_found": 0,
                "elapsed_ms": 100,
                "error": "timeout",
            }

        with patch(
            "jobforager.cli.commands.all_sources",
            return_value=["remotive", "hackernews"],
        ):
            with patch(
                "jobforager.cli.commands.run_health_probe",
                side_effect=fake_probe,
            ):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exit_code = main(["health"])

        self.assertEqual(exit_code, 1)
        rendered = output.getvalue()
        self.assertIn("source=hackernews status=fail", rendered)
        self.assertIn('error="timeout"', rendered)
        self.assertIn("summary total=2 ok=1 fail=1", rendered)

    def test_health_subset_sources(self) -> None:
        def fake_probe(source: str, timeout: float) -> dict:
            return {"status": "ok", "jobs_found": 1, "elapsed_ms": 100}

        with patch(
            "jobforager.cli.commands.run_health_probe",
            side_effect=fake_probe,
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(["health", "--sources", "remotive"])

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("source=remotive status=ok", rendered)
        self.assertNotIn("source=hackernews", rendered)
        self.assertIn("summary total=1 ok=1 fail=0", rendered)

    def test_health_missing_optional_deps(self) -> None:
        def fake_probe(source: str, timeout: float) -> dict:
            return {
                "status": "fail",
                "jobs_found": 0,
                "elapsed_ms": 0,
                "error": "python-jobspy not installed",
            }

        with patch(
            "jobforager.cli.commands.run_health_probe",
            side_effect=fake_probe,
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(["health", "--sources", "linkedin"])

        self.assertEqual(exit_code, 1)
        rendered = output.getvalue()
        self.assertIn("python-jobspy not installed", rendered)
        self.assertIn("summary total=1 ok=0 fail=1", rendered)

    def test_health_help(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                exit_code = main(["health", "--help"])
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 0

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("--sources", rendered)
        self.assertIn("--timeout", rendered)


if __name__ == "__main__":
    unittest.main()
