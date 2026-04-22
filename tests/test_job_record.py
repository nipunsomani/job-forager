from __future__ import annotations

import unittest

from jobforager.models import JobRecord


class TestJobRecord(unittest.TestCase):
    def test_valid_construction(self) -> None:
        job = JobRecord(
            source="remotive",
            title="Senior Python Engineer",
            company="Example Labs",
            job_url="https://jobs.example.com/roles/1",
            remote_type="remote",
            salary_min_usd=120000,
            salary_max_usd=150000,
            tags=["python", "fastapi"],
        )
        self.assertEqual(job.source, "remotive")
        self.assertEqual(job.title, "Senior Python Engineer")
        self.assertEqual(job.company, "Example Labs")
        self.assertEqual(job.job_url, "https://jobs.example.com/roles/1")
        self.assertEqual(job.remote_type, "remote")
        self.assertEqual(job.salary_min_usd, 120000)
        self.assertEqual(job.salary_max_usd, 150000)
        self.assertEqual(job.tags, ["python", "fastapi"])

    def test_empty_source_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "source must be a non-empty string"):
            JobRecord(source="", title="T", company="C", job_url="U")

    def test_empty_title_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "title must be a non-empty string"):
            JobRecord(source="S", title="", company="C", job_url="U")

    def test_empty_company_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "company must be a non-empty string"):
            JobRecord(source="S", title="T", company="", job_url="U")

    def test_empty_job_url_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "job_url must be a non-empty string"):
            JobRecord(source="S", title="T", company="C", job_url="")

    def test_invalid_remote_type_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "remote_type must be one of"):
            JobRecord(
                source="S", title="T", company="C", job_url="U", remote_type="orbital"
            )

    def test_negative_salary_min_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "salary_min_usd must be non-negative"):
            JobRecord(
                source="S", title="T", company="C", job_url="U", salary_min_usd=-1
            )

    def test_negative_salary_max_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "salary_max_usd must be non-negative"):
            JobRecord(
                source="S", title="T", company="C", job_url="U", salary_max_usd=-1
            )

    def test_invalid_tags_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "tags must be a list of strings"):
            JobRecord(
                source="S", title="T", company="C", job_url="U", tags=["ok", 123]
            )


if __name__ == "__main__":
    unittest.main()
