from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import unittest

from jobforager.cli import main


class TestCliDryRun(unittest.TestCase):
    def setUp(self) -> None:
        self.profile_path = (
            Path(__file__).resolve().parents[1] / "config" / "profile.example.toml"
        )

    def test_hunt_dry_run_smoke(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                ["hunt", "--dry-run", "--profile", str(self.profile_path)]
            )

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("job-forager dry run", rendered)
        self.assertIn("sources_enabled=", rendered)
        self.assertIn("records=", rendered)
        self.assertIn("dedupe_key=", rendered)
        self.assertIn("summary total_records=", rendered)
        self.assertIn("summary unique=", rendered)
        self.assertIn("duplicates=", rendered)
        self.assertIn("summary by_source", rendered)
        self.assertIn("summary by_remote_type", rendered)
        self.assertIn("status=completed_clean", rendered)

    def test_hunt_dry_run_with_records_file(self) -> None:
        records_path = (
            Path(__file__).resolve().parents[1] / "config" / "sample_records.json"
        )

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                [
                    "hunt",
                    "--dry-run",
                    "--profile",
                    str(self.profile_path),
                    "--records",
                    str(records_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("job-forager dry run", rendered)
        self.assertIn("sources_enabled=file", rendered)
        self.assertIn("Example Labs", rendered)
        self.assertIn("Data Co", rendered)
        self.assertIn("summary total_records=", rendered)
        self.assertIn("summary unique=", rendered)
        self.assertIn("duplicates=", rendered)
        self.assertIn("summary by_source", rendered)
        self.assertIn("summary by_remote_type", rendered)

    def test_hunt_dry_run_output_json(self) -> None:
        records_path = (
            Path(__file__).resolve().parents[1] / "config" / "sample_records.json"
        )
        out_json = Path(__file__).resolve().parent / ".tmp" / "test_out.json"
        out_json.parent.mkdir(exist_ok=True)
        if out_json.exists():
            out_json.unlink()

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                [
                    "hunt",
                    "--dry-run",
                    "--profile",
                    str(self.profile_path),
                    "--records",
                    str(records_path),
                    "--output-json",
                    str(out_json),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(out_json.exists())
        data = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 2)
        self.assertIn("dedupe_key", data[0])
        rendered = output.getvalue()
        self.assertIn("export_json records=2", rendered)
        self.assertIn("wrote_json=", rendered)
        out_json.unlink(missing_ok=True)

    def test_hunt_dry_run_output_csv(self) -> None:
        records_path = (
            Path(__file__).resolve().parents[1] / "config" / "sample_records.json"
        )
        out_csv = Path(__file__).resolve().parent / ".tmp" / "test_out.csv"
        out_csv.parent.mkdir(exist_ok=True)
        if out_csv.exists():
            out_csv.unlink()

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                [
                    "hunt",
                    "--dry-run",
                    "--profile",
                    str(self.profile_path),
                    "--records",
                    str(records_path),
                    "--output-csv",
                    str(out_csv),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(out_csv.exists())
        text = out_csv.read_text(encoding="utf-8")
        self.assertIn("dedupe_key", text)
        self.assertIn("Example Labs", text)
        rendered = output.getvalue()
        self.assertIn("export_csv records=2", rendered)
        self.assertIn("wrote_csv=", rendered)
        out_csv.unlink(missing_ok=True)

    def test_hunt_dry_run_skips_malformed_records(self) -> None:
        tmp_dir = Path(__file__).resolve().parent / ".tmp"
        tmp_dir.mkdir(exist_ok=True)
        records_path = tmp_dir / "malformed_records.json"
        records_path.write_text(
            json.dumps(
                [
                    {
                        "source": "remotive",
                        "title": "Senior Software Engineer",
                        "company": "Good Co",
                        "job_url": "https://example.com/1",
                        "remote_type": "remote",
                        "location": "City, Country",
                        "tags": ["python", "fastapi"],
                    },
                    {
                        "source": "remotive",
                        "title": "",
                        "company": "Bad Co",
                        "job_url": "https://example.com/2",
                    },
                ]
            ),
            encoding="utf-8",
        )

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                [
                    "hunt",
                    "--dry-run",
                    "--profile",
                    str(self.profile_path),
                    "--records",
                    str(records_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Senior Software Engineer", rendered)
        self.assertIn("Good Co", rendered)
        self.assertNotIn("Bad Co", rendered)
        self.assertIn("skipped_records=1", rendered)
        self.assertIn("  1.", rendered)
        self.assertIn("status=completed_with_skipped_records", rendered)
        records_path.unlink(missing_ok=True)

    def test_hunt_dry_run_empty_explicit_records_file(self) -> None:
        tmp_dir = Path(__file__).resolve().parent / ".tmp"
        tmp_dir.mkdir(exist_ok=True)
        empty_records = tmp_dir / "empty_records.json"
        empty_records.write_text("[]", encoding="utf-8")

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                [
                    "hunt",
                    "--dry-run",
                    "--profile",
                    str(self.profile_path),
                    "--records",
                    str(empty_records),
                ]
            )

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("sources_enabled=file", rendered)
        self.assertNotIn("Example Labs", rendered)
        self.assertIn("records=0", rendered)
        self.assertIn("status=completed_clean", rendered)
        empty_records.unlink(missing_ok=True)

    def test_validate_command_shows_profile_summary(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                ["validate", "--profile", str(self.profile_path)]
            )

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("job-forager validate", rendered)
        self.assertIn("profile_status=ok", rendered)
        self.assertIn("profile_summary", rendered)
        self.assertIn("sources_enabled=", rendered)
        self.assertIn("filters_active=", rendered)

    def test_hunt_dry_run_missing_records_file(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                [
                    "hunt",
                    "--dry-run",
                    "--profile",
                    str(self.profile_path),
                    "--records",
                    "nonexistent_file.json",
                ]
            )

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("job-forager dry run", rendered)
        self.assertIn("error source=file", rendered)
        self.assertIn("status=completed_with_collector_errors", rendered)

    def test_validate_command_reports_invalid_profile(self) -> None:
        tmp_dir = Path(__file__).resolve().parent / ".tmp"
        tmp_dir.mkdir(exist_ok=True)
        bad_profile = tmp_dir / "bad_profile.toml"
        bad_profile.write_text("not_valid_toml = [", encoding="utf-8")

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                ["validate", "--profile", str(bad_profile)]
            )

        self.assertEqual(exit_code, 1)
        rendered = output.getvalue()
        self.assertIn("validate error:", rendered)
        bad_profile.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
