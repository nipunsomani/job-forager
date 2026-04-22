from __future__ import annotations

import unittest

from jobforager.normalize.ats_detector import detect_ats_from_record, detect_ats_platform


class TestDetectAtsPlatform(unittest.TestCase):
    def test_greenhouse(self) -> None:
        self.assertEqual(
            detect_ats_platform("https://boards.greenhouse.io/stripe/jobs/123"),
            "greenhouse",
        )

    def test_greenhouse_job_boards(self) -> None:
        self.assertEqual(
            detect_ats_platform("https://job-boards.greenhouse.io/airbnb/jobs/456"),
            "greenhouse",
        )

    def test_lever(self) -> None:
        self.assertEqual(
            detect_ats_platform("https://jobs.lever.co/netflix/abc-123"),
            "lever",
        )

    def test_ashby(self) -> None:
        self.assertEqual(
            detect_ats_platform("https://jobs.ashbyhq.com/supabase/1"),
            "ashby",
        )

    def test_workday(self) -> None:
        self.assertEqual(
            detect_ats_platform("https://wd1.myworkdayjobs.com/amazon/jobs/123"),
            "workday",
        )

    def test_rippling(self) -> None:
        self.assertEqual(
            detect_ats_platform("https://ats.rippling.com/acme/jobs/789"),
            "rippling",
        )

    def test_workable(self) -> None:
        self.assertEqual(
            detect_ats_platform("https://apply.workable.com/acme/j/123"),
            "workable",
        )

    def test_none(self) -> None:
        self.assertIsNone(detect_ats_platform(None))

    def test_empty(self) -> None:
        self.assertIsNone(detect_ats_platform(""))

    def test_unknown(self) -> None:
        self.assertIsNone(detect_ats_platform("https://example.com/careers"))

    def test_case_insensitive(self) -> None:
        self.assertEqual(
            detect_ats_platform("https://JOBS.LEVER.CO/NETFLIX/ABC"),
            "lever",
        )


class TestDetectAtsFromRecord(unittest.TestCase):
    def test_from_job_url(self) -> None:
        record = {"job_url": "https://boards.greenhouse.io/stripe/jobs/1"}
        self.assertEqual(detect_ats_from_record(record), "greenhouse")

    def test_from_apply_url(self) -> None:
        record = {
            "job_url": "https://example.com",
            "apply_url": "https://jobs.lever.co/netflix/apply",
        }
        self.assertEqual(detect_ats_from_record(record), "lever")

    def test_from_source(self) -> None:
        record = {"source": "ashby", "job_url": "https://example.com"}
        self.assertEqual(detect_ats_from_record(record), "ashby")

    def test_no_detection(self) -> None:
        record = {"source": "remotive", "job_url": "https://remotive.com/job/1"}
        self.assertIsNone(detect_ats_from_record(record))

    def test_job_url_takes_precedence(self) -> None:
        record = {
            "source": "remotive",
            "job_url": "https://boards.greenhouse.io/stripe/jobs/1",
        }
        self.assertEqual(detect_ats_from_record(record), "greenhouse")


if __name__ == "__main__":
    unittest.main()
