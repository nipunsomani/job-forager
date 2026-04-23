from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from jobforager.models import JobRecord
from jobforager.search import (
    apply_search_filters,
    filter_by_date,
    filter_by_keywords,
    filter_by_location,
)


class TestSearchFilters(unittest.TestCase):
    def _make_job(
        self,
        title: str = "Engineer",
        company: str = "Test Co",
        location: str | None = "Remote",
        description: str | None = "Build things.",
        tags: list[str] | None = None,
        posted_at: datetime | None = None,
    ) -> JobRecord:
        return JobRecord(
            source="test",
            title=title,
            company=company,
            job_url="https://example.com/jobs/1",
            location=location,
            description=description,
            tags=tags or [],
            posted_at=posted_at,
        )

    def test_filter_by_keywords_empty(self) -> None:
        jobs = [
            self._make_job(title="Python Dev"),
            self._make_job(title="Java Dev"),
        ]
        result = filter_by_keywords(jobs, [])
        self.assertEqual(len(result), 2)

    def test_filter_by_keywords_title_match(self) -> None:
        jobs = [
            self._make_job(title="Python Developer"),
            self._make_job(title="Java Developer"),
        ]
        result = filter_by_keywords(jobs, ["python"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Python Developer")

    def test_filter_by_keywords_company_match(self) -> None:
        jobs = [
            self._make_job(company="Acme Corp"),
            self._make_job(company="Beta Inc"),
        ]
        result = filter_by_keywords(jobs, ["acme"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].company, "Acme Corp")

    def test_filter_by_keywords_tags_match(self) -> None:
        jobs = [
            self._make_job(tags=["python", "fastapi"]),
            self._make_job(tags=["java", "spring"]),
        ]
        result = filter_by_keywords(jobs, ["fastapi"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].tags, ["python", "fastapi"])

    def test_filter_by_keywords_description_match(self) -> None:
        jobs = [
            self._make_job(description="We use kubernetes and docker."),
            self._make_job(description="We use java and sql."),
        ]
        result = filter_by_keywords(jobs, ["kubernetes"])
        self.assertEqual(len(result), 1)
        self.assertIn("kubernetes", result[0].description or "")

    def test_filter_by_keywords_none_fields(self) -> None:
        job = JobRecord(
            source="test",
            title="Role",
            company="Co",
            job_url="https://example.com/jobs/1",
            location=None,
            description=None,
            tags=[],
        )
        result = filter_by_keywords([job], ["python"])
        self.assertEqual(len(result), 0)

    def test_filter_by_keywords_multiple_keywords(self) -> None:
        jobs = [
            self._make_job(title="Python Engineer"),
            self._make_job(title="Rust Engineer"),
        ]
        result = filter_by_keywords(jobs, ["python", "rust"])
        self.assertEqual(len(result), 2)

    def test_filter_by_location_empty(self) -> None:
        jobs = [self._make_job(location="Remote")]
        result = filter_by_location(jobs, None)
        self.assertEqual(len(result), 1)

    def test_filter_by_location_match(self) -> None:
        jobs = [
            self._make_job(location="London, UK"),
            self._make_job(location="New York, USA"),
        ]
        result = filter_by_location(jobs, "london")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].location, "London, UK")

    def test_filter_by_location_keeps_none(self) -> None:
        jobs = [
            self._make_job(location=None),
            self._make_job(location="London"),
        ]
        result = filter_by_location(jobs, "london")
        self.assertEqual(len(result), 2)

    def test_filter_by_date_empty(self) -> None:
        jobs = [self._make_job()]
        result = filter_by_date(jobs, None, None)
        self.assertEqual(len(result), 1)

    def test_filter_by_date_since(self) -> None:
        since = datetime(2024, 1, 15, tzinfo=timezone.utc)
        jobs = [
            self._make_job(posted_at=datetime(2024, 1, 10, tzinfo=timezone.utc)),
            self._make_job(posted_at=datetime(2024, 1, 20, tzinfo=timezone.utc)),
            self._make_job(posted_at=None),
        ]
        result = filter_by_date(jobs, since, None)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].posted_at, datetime(2024, 1, 20, tzinfo=timezone.utc))
        self.assertIsNone(result[1].posted_at)

    def test_filter_by_date_last_duration(self) -> None:
        now = datetime.now(timezone.utc)
        jobs = [
            self._make_job(posted_at=now - timedelta(days=10)),
            self._make_job(posted_at=now - timedelta(days=2)),
        ]
        result = filter_by_date(jobs, None, timedelta(days=7))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].posted_at, now - timedelta(days=2))

    def test_filter_by_date_combined_cutoff(self) -> None:
        since = datetime(2024, 1, 10, tzinfo=timezone.utc)
        jobs = [
            self._make_job(posted_at=datetime(2024, 1, 5, tzinfo=timezone.utc)),
            self._make_job(posted_at=datetime(2024, 1, 12, tzinfo=timezone.utc)),
        ]
        result = filter_by_date(jobs, since, timedelta(days=5000))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].posted_at, datetime(2024, 1, 12, tzinfo=timezone.utc))

    def test_apply_search_filters_combined(self) -> None:
        since = datetime(2024, 1, 15, tzinfo=timezone.utc)
        jobs = [
            self._make_job(
                title="Python Developer",
                location="Remote",
                posted_at=datetime(2024, 1, 20, tzinfo=timezone.utc),
            ),
            self._make_job(
                title="Java Developer",
                location="London",
                posted_at=datetime(2024, 1, 20, tzinfo=timezone.utc),
            ),
            self._make_job(
                title="Python Developer",
                location="Remote",
                posted_at=datetime(2024, 1, 10, tzinfo=timezone.utc),
            ),
        ]
        result = apply_search_filters(
            jobs,
            keywords=["python"],
            location_query="remote",
            since=since,
            last_duration=None,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Python Developer")

    def test_filter_by_title_keywords_match(self) -> None:
        from jobforager.search import filter_by_title_keywords
        jobs = [
            self._make_job(title="Security Engineer"),
            self._make_job(title="Software Developer"),
        ]
        result = filter_by_title_keywords(jobs, ["Security"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Security Engineer")

    def test_filter_by_title_keywords_no_match(self) -> None:
        from jobforager.search import filter_by_title_keywords
        jobs = [
            self._make_job(title="Software Developer"),
            self._make_job(title="Data Scientist"),
        ]
        result = filter_by_title_keywords(jobs, ["Security"])
        self.assertEqual(len(result), 0)

    def test_filter_by_title_keywords_ignores_description(self) -> None:
        from jobforager.search import filter_by_title_keywords
        jobs = [
            self._make_job(title="Software Developer", description="We need security expertise."),
            self._make_job(title="Security Engineer", description="Build secure systems."),
        ]
        result = filter_by_title_keywords(jobs, ["security"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Security Engineer")

    def test_filter_by_desc_keywords_match(self) -> None:
        from jobforager.search import filter_by_desc_keywords
        jobs = [
            self._make_job(description="Experience with AWS required."),
            self._make_job(description="Experience with Azure required."),
        ]
        result = filter_by_desc_keywords(jobs, ["AWS"])
        self.assertEqual(len(result), 1)
        self.assertIn("AWS", result[0].description or "")

    def test_filter_by_desc_keywords_ignores_title(self) -> None:
        from jobforager.search import filter_by_desc_keywords
        jobs = [
            self._make_job(title="AWS Engineer", description="General engineering."),
            self._make_job(title="DevOps Engineer", description="Experience with AWS required."),
        ]
        result = filter_by_desc_keywords(jobs, ["aws"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "DevOps Engineer")

    def test_apply_search_filters_with_title_keywords(self) -> None:
        from jobforager.search import apply_search_filters
        jobs = [
            self._make_job(title="Security Engineer", description="We use python."),
            self._make_job(title="Python Developer", description="Security background preferred."),
        ]
        result = apply_search_filters(
            jobs,
            keywords=["python"],
            location_query=None,
            since=None,
            last_duration=None,
            title_keywords=["Security"],
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Security Engineer")

    def test_filter_by_location_uk_alias(self) -> None:
        jobs = [
            self._make_job(location="United Kingdom"),
            self._make_job(location="London, UK"),
            self._make_job(location="New York, US"),
            self._make_job(location="Remote"),
        ]
        result = filter_by_location(jobs, "UK")
        self.assertEqual(len(result), 3)
        self.assertEqual(
            [j.location for j in result],
            ["United Kingdom", "London, UK", "Remote"],
        )

    def test_filter_by_location_london_query(self) -> None:
        jobs = [
            self._make_job(location="London"),
            self._make_job(location="London, UK"),
            self._make_job(location="Manchester, UK"),
            self._make_job(location="New York"),
        ]
        result = filter_by_location(jobs, "London")
        self.assertEqual(len(result), 2)
        self.assertEqual(
            [j.location for j in result],
            ["London", "London, UK"],
        )


if __name__ == "__main__":
    unittest.main()
