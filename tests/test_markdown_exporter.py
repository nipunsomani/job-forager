from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path

from jobforager.exporters import write_normalized_markdown
from jobforager.models import JobRecord


class TestMarkdownExporter(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(__file__).resolve().parent / ".tmp"
        self.tmp_dir.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        for path in self.tmp_dir.iterdir():
            if path.is_file():
                path.unlink()

    def test_empty_records(self) -> None:
        path = self.tmp_dir / "empty.md"
        write_normalized_markdown([], [], path, header_title="New Jobs")
        text = path.read_text(encoding="utf-8")
        self.assertIn("# 0 New Jobs", text)
        self.assertNotIn("##", text)

    def test_grouped_by_source_and_sorted(self) -> None:
        jobs = [
            JobRecord(source="lever", title="Job B", company="Co B", job_url="https://b"),
            JobRecord(source="greenhouse", title="Job A", company="Co A", job_url="https://a"),
            JobRecord(source="lever", title="Job C", company="Co C", job_url="https://c"),
        ]
        path = self.tmp_dir / "grouped.md"
        write_normalized_markdown(jobs, ["k1", "k2", "k3"], path)
        text = path.read_text(encoding="utf-8")

        # Sources should appear alphabetically (source names are lowercase)
        greenhouse_pos = text.index("## greenhouse")
        lever_pos = text.index("## lever")
        self.assertLess(greenhouse_pos, lever_pos)

        self.assertIn("## greenhouse (1)", text)
        self.assertIn("## lever (2)", text)

    def test_numbered_within_source(self) -> None:
        jobs = [
            JobRecord(source="greenhouse", title="First", company="A", job_url="https://a"),
            JobRecord(source="greenhouse", title="Second", company="B", job_url="https://b"),
        ]
        path = self.tmp_dir / "numbered.md"
        write_normalized_markdown(jobs, ["k1", "k2"], path)
        text = path.read_text(encoding="utf-8")
        self.assertIn("1. **First** @ A", text)
        self.assertIn("2. **Second** @ B", text)

    def test_all_fields_present(self) -> None:
        posted = datetime(2026, 4, 23, 9, 0, 0)
        job = JobRecord(
            source="greenhouse",
            title="Senior Security Engineer",
            company="Stripe",
            job_url="https://boards.greenhouse.io/stripe/jobs/12345",
            location="Remote, US",
            salary_raw="$180k-$250k",
            posted_at=posted,
            apply_url="https://boards.greenhouse.io/stripe/jobs/12345/apply",
        )
        path = self.tmp_dir / "full.md"
        write_normalized_markdown([job], ["k1"], path)
        text = path.read_text(encoding="utf-8")

        self.assertIn("**Senior Security Engineer** @ Stripe", text)
        self.assertIn("Location: Remote, US", text)
        self.assertIn("Salary: $180k-$250k", text)
        self.assertIn("Posted: 2026-04-23T09:00:00", text)
        self.assertIn("[Apply](https://boards.greenhouse.io/stripe/jobs/12345/apply)", text)

    def test_missing_fields_omitted(self) -> None:
        job = JobRecord(
            source="greenhouse",
            title="Mystery Job",
            company="Ghost",
            job_url="https://ghost.co",
        )
        path = self.tmp_dir / "minimal.md"
        write_normalized_markdown([job], ["k1"], path)
        text = path.read_text(encoding="utf-8")

        self.assertIn("**Mystery Job** @ Ghost", text)
        self.assertNotIn("Location:", text)
        self.assertNotIn("Salary:", text)
        self.assertNotIn("Posted:", text)
        # Should still have apply link fallback to job_url
        self.assertIn("[Apply](https://ghost.co)", text)

    def test_salary_from_min_max(self) -> None:
        job = JobRecord(
            source="greenhouse",
            title="Engineer",
            company="X",
            job_url="https://x",
            salary_min_usd=100000,
            salary_max_usd=150000,
        )
        path = self.tmp_dir / "salary_range.md"
        write_normalized_markdown([job], ["k1"], path)
        text = path.read_text(encoding="utf-8")
        self.assertIn("Salary: $100,000-$150,000", text)

    def test_salary_min_only(self) -> None:
        job = JobRecord(
            source="greenhouse",
            title="Engineer",
            company="X",
            job_url="https://x",
            salary_min_usd=50000,
        )
        path = self.tmp_dir / "salary_min.md"
        write_normalized_markdown([job], ["k1"], path)
        text = path.read_text(encoding="utf-8")
        self.assertIn("Salary: $50,000+", text)

    def test_salary_max_only(self) -> None:
        job = JobRecord(
            source="greenhouse",
            title="Engineer",
            company="X",
            job_url="https://x",
            salary_max_usd=90000,
        )
        path = self.tmp_dir / "salary_max.md"
        write_normalized_markdown([job], ["k1"], path)
        text = path.read_text(encoding="utf-8")
        self.assertIn("Salary: Up to $90,000", text)

    def test_apply_url_fallback_to_job_url(self) -> None:
        job = JobRecord(
            source="greenhouse",
            title="T",
            company="C",
            job_url="https://job",
            apply_url=None,
        )
        path = self.tmp_dir / "fallback.md"
        write_normalized_markdown([job], ["k1"], path)
        text = path.read_text(encoding="utf-8")
        self.assertIn("[Apply](https://job)", text)


if __name__ == "__main__":
    unittest.main()
