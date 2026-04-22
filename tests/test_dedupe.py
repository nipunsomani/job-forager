from __future__ import annotations

import unittest

from jobforager.models import JobRecord
from jobforager.normalize import build_dedupe_key


class TestDedupeKey(unittest.TestCase):
    def test_external_id_takes_priority(self) -> None:
        job = JobRecord(
            source="the-muse",
            title="Backend Engineer",
            company="Data Co",
            job_url="https://muse.example/jobs/42",
            external_id="MUSE-42",
        )

        dedupe_key = build_dedupe_key(job)
        self.assertIn("external_id", dedupe_key)
        self.assertIn("muse-42", dedupe_key)

    def test_hash_key_is_deterministic(self) -> None:
        job_a = JobRecord(
            source=" Remotive ",
            title="Senior Python Engineer",
            company="Example Labs",
            job_url="https://jobs.example.com/roles/1",
        )
        job_b = JobRecord(
            source="remotive",
            title="senior python engineer",
            company="EXAMPLE LABS",
            job_url="https://jobs.example.com/roles/1",
        )

        self.assertEqual(build_dedupe_key(job_a), build_dedupe_key(job_b))


if __name__ == "__main__":
    unittest.main()
