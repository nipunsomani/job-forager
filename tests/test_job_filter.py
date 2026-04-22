from __future__ import annotations

import unittest

from jobforager.models import CandidateProfile, JobRecord
from jobforager.normalize import filter_jobs


class TestJobFilter(unittest.TestCase):
    def _make_job(
        self,
        title: str = "Engineer",
        location: str | None = "Remote",
        remote_type: str | None = "remote",
        salary_max_usd: int | None = 150000,
        tags: list[str] | None = None,
    ) -> JobRecord:
        return JobRecord(
            source="test",
            title=title,
            company="Test Co",
            job_url="https://example.com/jobs/1",
            location=location,
            remote_type=remote_type,
            salary_max_usd=salary_max_usd,
            tags=tags or [],
        )

    def test_empty_profile_passes_all(self) -> None:
        profile = CandidateProfile()
        jobs = [
            self._make_job(title="A", remote_type="onsite"),
            self._make_job(title="B", remote_type="remote"),
        ]
        result = filter_jobs(jobs, profile)
        self.assertEqual(len(result), 2)

    def test_remote_only_excludes_hybrid_and_onsite(self) -> None:
        profile = CandidateProfile(remote_preference="remote_only")
        jobs = [
            self._make_job(remote_type="remote"),
            self._make_job(remote_type="hybrid"),
            self._make_job(remote_type="onsite"),
            self._make_job(remote_type="unknown"),
            self._make_job(remote_type=None),
        ]
        result = filter_jobs(jobs, profile)
        self.assertEqual([j.remote_type for j in result], ["remote"])

    def test_remote_preferred_allows_hybrid(self) -> None:
        profile = CandidateProfile(remote_preference="remote_preferred")
        jobs = [
            self._make_job(remote_type="remote"),
            self._make_job(remote_type="hybrid"),
            self._make_job(remote_type="onsite"),
        ]
        result = filter_jobs(jobs, profile)
        self.assertEqual([j.remote_type for j in result], ["remote", "hybrid"])

    def test_hybrid_ok_allows_onsite(self) -> None:
        profile = CandidateProfile(remote_preference="hybrid_ok")
        jobs = [
            self._make_job(remote_type="remote"),
            self._make_job(remote_type="hybrid"),
            self._make_job(remote_type="onsite"),
        ]
        result = filter_jobs(jobs, profile)
        self.assertEqual([j.remote_type for j in result], ["remote", "hybrid", "onsite"])

    def test_locations_filter_matches_substring(self) -> None:
        profile = CandidateProfile(locations=["London", "UK"])
        jobs = [
            self._make_job(location="London, UK"),
            self._make_job(location="Remote"),
            self._make_job(location="New York"),
        ]
        result = filter_jobs(jobs, profile)
        self.assertEqual([j.location for j in result], ["London, UK"])

    def test_locations_filter_keeps_none_location(self) -> None:
        profile = CandidateProfile(locations=["London"])
        jobs = [
            self._make_job(location=None),
            self._make_job(location="London"),
        ]
        result = filter_jobs(jobs, profile)
        self.assertEqual(len(result), 2)

    def test_titles_filter_matches_substring(self) -> None:
        profile = CandidateProfile(target_titles=["Senior", "Staff"])
        jobs = [
            self._make_job(title="Senior Engineer"),
            self._make_job(title="Junior Engineer"),
            self._make_job(title="Staff Engineer"),
        ]
        result = filter_jobs(jobs, profile)
        self.assertEqual([j.title for j in result], ["Senior Engineer", "Staff Engineer"])

    def test_skills_filter_requires_overlap(self) -> None:
        profile = CandidateProfile(skills=["python", "fastapi"])
        jobs = [
            self._make_job(title="Python Dev", tags=["python", "django"]),
            self._make_job(title="Java Dev", tags=["java", "spring"]),
            self._make_job(title="No Tags Dev", tags=[]),
        ]
        result = filter_jobs(jobs, profile)
        self.assertEqual([j.title for j in result], ["Python Dev", "No Tags Dev"])

    def test_skills_filter_allows_empty_tags(self) -> None:
        profile = CandidateProfile(skills=["python"])
        jobs = [
            self._make_job(tags=[]),
            self._make_job(tags=["python"]),
        ]
        result = filter_jobs(jobs, profile)
        self.assertEqual(len(result), 2)

    def test_salary_floor_excludes_below(self) -> None:
        profile = CandidateProfile(salary_floor_usd=120000)
        jobs = [
            self._make_job(salary_max_usd=150000),
            self._make_job(salary_max_usd=100000),
            self._make_job(salary_max_usd=120000),
        ]
        result = filter_jobs(jobs, profile)
        self.assertEqual([j.salary_max_usd for j in result], [150000, 120000])

    def test_salary_floor_allows_missing_salary(self) -> None:
        profile = CandidateProfile(salary_floor_usd=120000)
        jobs = [
            self._make_job(salary_max_usd=None),
            self._make_job(salary_max_usd=150000),
        ]
        result = filter_jobs(jobs, profile)
        self.assertEqual(len(result), 2)

    def test_combined_filters(self) -> None:
        profile = CandidateProfile(
            remote_preference="remote_only",
            target_titles=["Python"],
            skills=["python"],
            salary_floor_usd=100000,
        )
        jobs = [
            self._make_job(
                title="Python Engineer",
                remote_type="remote",
                salary_max_usd=120000,
                tags=["python"],
            ),
            self._make_job(
                title="Java Engineer",
                remote_type="remote",
                salary_max_usd=120000,
                tags=["java"],
            ),
            self._make_job(
                title="Python Engineer",
                remote_type="hybrid",
                salary_max_usd=120000,
                tags=["python"],
            ),
        ]
        result = filter_jobs(jobs, profile)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Python Engineer")


if __name__ == "__main__":
    unittest.main()
