from __future__ import annotations

import unittest

from jobforager.normalize import normalize_raw_job_record


class TestJobNormalizer(unittest.TestCase):
    def test_normalize_raw_job_record_maps_fields(self) -> None:
        raw_record = {
            "source": "remotive",
            "title": "Senior Python Engineer",
            "company": "Example Labs",
            "job_url": "https://jobs.example.com/roles/1",
            "location": "Remote",
            "remote_type": "remote",
            "salary_raw": "$120k-$150k",
            "salary_min_usd": "120000",
            "salary_max_usd": 150000,
            "apply_url": "https://jobs.example.com/roles/1/apply",
            "external_id": "r-1",
            "description": "Build APIs.",
            "tags": ["python", "fastapi"],
        }

        job = normalize_raw_job_record(raw_record)

        self.assertEqual(job.source, "remotive")
        self.assertEqual(job.title, "Senior Python Engineer")
        self.assertEqual(job.company, "Example Labs")
        self.assertEqual(job.job_url, "https://jobs.example.com/roles/1")
        self.assertEqual(job.salary_min_usd, 120000)
        self.assertEqual(job.salary_max_usd, 150000)
        self.assertEqual(job.tags, ["python", "fastapi"])

    def test_unknown_fields_are_captured_in_metadata(self) -> None:
        raw_record = {
            "source": "themuse",
            "title": "Backend Engineer",
            "company": "Data Co",
            "job_url": "https://muse.example/jobs/42",
            "metadata": {"seed": "base"},
            "raw_rank": 99,
            "ingest_batch": "batch-1",
        }

        job = normalize_raw_job_record(raw_record)

        self.assertEqual(job.metadata["seed"], "base")
        self.assertEqual(job.metadata["raw_rank"], 99)
        self.assertEqual(job.metadata["ingest_batch"], "batch-1")


if __name__ == "__main__":
    unittest.main()
