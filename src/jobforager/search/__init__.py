"""Search-specific filter utilities for JobRecord objects."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jobforager.models.job_record import JobRecord

__all__ = [
    "filter_by_keywords",
    "filter_by_excluded_keywords",
    "filter_by_location",
    "filter_by_date",
    "filter_by_experience_level",
    "filter_by_recruiter",
    "apply_search_filters",
]


def filter_by_keywords(
    records: list[JobRecord], keywords: list[str] | None
) -> list[JobRecord]:
    """
    Filter records by keywords across title, company, tags, and description.

    Args:
        records: List of JobRecord objects to filter.
        keywords: List of keywords to search for. If None or empty, returns
            all records unchanged.

    Returns:
        List of records where at least one keyword (case-insensitive) appears
        in title, company, tags, or description.
    """
    if not keywords:
        return records

    matched: list[JobRecord] = []
    keyword_lower = [kw.lower() for kw in keywords]

    for job in records:
        if job.title and any(kw in job.title.lower() for kw in keyword_lower):
            matched.append(job)
            continue

        if job.company and any(kw in job.company.lower() for kw in keyword_lower):
            matched.append(job)
            continue

        if job.tags and any(
            kw in tag.lower() for tag in job.tags for kw in keyword_lower
        ):
            matched.append(job)
            continue

        if job.description and any(
            kw in job.description.lower() for kw in keyword_lower
        ):
            matched.append(job)
            continue

    return matched


def filter_by_location(
    records: list[JobRecord], location_query: str | None
) -> list[JobRecord]:
    """
    Filter records by location substring match.

    Args:
        records: List of JobRecord objects to filter.
        location_query: Location string to search for. If None or empty,
            returns all records unchanged.

    Returns:
        List of records where location contains the query (case-insensitive),
        or where location is None.
    """
    if not location_query or not location_query.strip():
        return records

    query_lower = location_query.lower()

    return [
        job
        for job in records
        if job.location is None or query_lower in job.location.lower()
    ]


def filter_by_date(
    records: list[JobRecord],
    since: datetime | None,
    last_duration: timedelta | None,
) -> list[JobRecord]:
    """
    Filter records by posted_at date.

    Args:
        records: List of JobRecord objects to filter.
        since: Keep records where posted_at >= since (or posted_at is None).
        last_duration: If provided, compute cutoff = now_utc - last_duration.
            Keep records where posted_at >= cutoff (or posted_at is None).

    Returns:
        List of records matching the date criteria.
    """
    if since is None and last_duration is None:
        return records

    cutoff: datetime | None = None

    if last_duration is not None:
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - last_duration

    if since is not None:
        if cutoff is None:
            cutoff = since
        else:
            cutoff = max(cutoff, since)

    # Normalize cutoff to UTC-aware
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)

    def is_recent(posted: datetime | None) -> bool:
        if posted is None:
            return True
        # Normalize posted to UTC-aware
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        return posted >= cutoff  # type: ignore[arg-type]

    return [job for job in records if is_recent(job.posted_at)]


def filter_by_excluded_keywords(
    records: list[JobRecord], excluded: list[str] | None
) -> list[JobRecord]:
    if not excluded:
        return records

    excluded_lower = [kw.lower() for kw in excluded]

    def _has_excluded(job: JobRecord) -> bool:
        text = " ".join(
            filter(
                None,
                [
                    job.title,
                    job.company,
                    job.description,
                    *job.tags,
                ],
            )
        ).lower()
        return any(kw in text for kw in excluded_lower)

    return [job for job in records if not _has_excluded(job)]


def filter_by_experience_level(
    records: list[JobRecord], level: str | None
) -> list[JobRecord]:
    if not level:
        return records

    level = level.lower()
    valid_levels = {"intern", "entry", "mid", "senior"}
    if level not in valid_levels:
        return records

    from jobforager.normalize.experience_level import extract_experience_level

    return [job for job in records if extract_experience_level(job.title) == level]


def filter_by_recruiter(
    records: list[JobRecord], hide_recruiters: bool
) -> list[JobRecord]:
    if not hide_recruiters:
        return records

    from jobforager.normalize.recruiter_detector import is_recruiter_company

    return [job for job in records if not is_recruiter_company(job.company)]


def apply_search_filters(
    records: list[JobRecord],
    keywords: list[str] | None,
    location_query: str | None,
    since: datetime | None,
    last_duration: timedelta | None,
    excluded: list[str] | None = None,
    level: str | None = None,
    hide_recruiters: bool = False,
) -> list[JobRecord]:
    result = filter_by_keywords(records, keywords)
    result = filter_by_excluded_keywords(result, excluded)
    result = filter_by_location(result, location_query)
    result = filter_by_date(result, since, last_duration)
    result = filter_by_experience_level(result, level)
    result = filter_by_recruiter(result, hide_recruiters)
    return result
