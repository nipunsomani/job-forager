from __future__ import annotations

import platform
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jobforager.storage import JobStore


class TestJobStore(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test.db"

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_creates_db_file_and_tables(self) -> None:
        self.assertFalse(self.db_path.exists())
        store = JobStore(str(self.db_path))
        self.assertTrue(self.db_path.exists())
        jobs = store.get_jobs_since(datetime(2000, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(jobs, [])
        self.assertIsNone(store.get_last_run_time())

    def test_upsert_jobs_inserts_new(self) -> None:
        store = JobStore(str(self.db_path))
        jobs = [
            {
                "source": "remotive",
                "title": "Engineer",
                "company": "Acme",
                "job_url": "https://example.com/1",
                "tags": ["python"],
                "metadata": {"foo": "bar"},
            }
        ]
        inserted, updated = store.upsert_jobs(jobs)
        self.assertEqual(inserted, 1)
        self.assertEqual(updated, 0)

        results = store.get_jobs_since(datetime(2000, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "remotive")
        self.assertEqual(results[0]["title"], "Engineer")
        self.assertEqual(results[0]["tags"], ["python"])
        self.assertEqual(results[0]["metadata"], {"foo": "bar"})

    def test_upsert_updates_last_seen_at_on_conflict(self) -> None:
        store = JobStore(str(self.db_path))
        jobs = [
            {
                "source": "remotive",
                "title": "Engineer",
                "company": "Acme",
                "job_url": "https://example.com/1",
            }
        ]
        store.upsert_jobs(jobs)

        results_before = store.get_jobs_since(datetime(2000, 1, 1, tzinfo=timezone.utc))
        first_seen = results_before[0]["first_seen_at"]
        last_seen_before = results_before[0]["last_seen_at"]

        inserted, updated = store.upsert_jobs(jobs)
        self.assertEqual(inserted, 0)
        self.assertEqual(updated, 1)

        results_after = store.get_jobs_since(datetime(2000, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(results_after[0]["first_seen_at"], first_seen)
        self.assertNotEqual(results_after[0]["last_seen_at"], last_seen_before)

    def test_get_last_run_time(self) -> None:
        store = JobStore(str(self.db_path))
        self.assertIsNone(store.get_last_run_time())

        store.record_run(["remotive"], "python", 5)
        last_run = store.get_last_run_time()
        self.assertIsNotNone(last_run)
        self.assertIsInstance(last_run, datetime)
        self.assertAlmostEqual(
            last_run.timestamp(),
            datetime.now(timezone.utc).timestamp(),
            delta=5,
        )

    def test_get_jobs_since_filters_correctly(self) -> None:
        store = JobStore(str(self.db_path))
        now = datetime.now(timezone.utc)

        jobs = [
            {
                "source": "remotive",
                "title": "Engineer",
                "company": "Acme",
                "job_url": "https://example.com/1",
            }
        ]
        store.upsert_jobs(jobs)

        results = store.get_jobs_since(now - timedelta(days=1))
        self.assertEqual(len(results), 1)

        results = store.get_jobs_since(now + timedelta(days=1))
        self.assertEqual(len(results), 0)

    def test_default_db_path_resolves_to_cache_dir(self) -> None:
        store = JobStore()
        path = Path(store.path)
        self.assertIn("jobforager", path.parts)
        self.assertEqual(path.name, "jobs.db")

        system = platform.system()
        if system == "Windows":
            self.assertIn("jobforager", path.parts)
        else:
            self.assertIn(".cache", path.parts)


if __name__ == "__main__":
    unittest.main()
