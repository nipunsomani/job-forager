"""JobSpy collector for LinkedIn, Indeed, and Glassdoor.

This module wraps the ``python-jobspy`` package to scrape major job boards.
"""

from __future__ import annotations

import math
from typing import Any

from jobspy import scrape_jobs

_DEFAULT_SEARCH_TERM = ""
_DEFAULT_RESULTS_WANTED = 50
_DEFAULT_HOURS_OLD = 168  # 7 days
# JobSpy search terms with many keywords often return empty; shard long queries.
_MAX_KEYWORDS_PER_SHARD = 3


def _is_valid_number(value: Any) -> bool:
    """Return True if *value* is a real number (not None or NaN)."""
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _map_jobspy_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Map a single JobSpy DataFrame row to a Job Forager raw record."""
    title = str(row.get("title") or "").strip()
    company = str(row.get("company") or "").strip()
    job_url = str(row.get("job_url") or "").strip()

    if not title or not company or not job_url:
        return None

    remote_type = None
    if row.get("is_remote") is True:
        remote_type = "remote"
    elif row.get("is_remote") is False:
        remote_type = "onsite"

    location = str(row.get("location") or "").strip() or None

    # Salary handling — guard against NaN from pandas
    min_amount = row.get("min_amount")
    max_amount = row.get("max_amount")
    currency = str(row.get("currency") or "").strip().upper()
    interval = str(row.get("interval") or "").strip().lower()

    salary_raw = None
    if _is_valid_number(min_amount) or _is_valid_number(max_amount):
        parts: list[str] = []
        if _is_valid_number(min_amount):
            parts.append(str(min_amount))
        if _is_valid_number(max_amount):
            parts.append(str(max_amount))
        if interval:
            parts.append(interval)
        if currency:
            parts.append(currency)
        salary_raw = " - ".join(parts)

    salary_min_usd = None
    salary_max_usd = None
    if currency == "USD" and _is_valid_number(min_amount):
        salary_min_usd = int(float(min_amount))
    if currency == "USD" and _is_valid_number(max_amount):
        salary_max_usd = int(float(max_amount))

    posted_at = str(row.get("date_posted") or "").strip() or None
    description = str(row.get("description") or "").strip() or None

    job_type = str(row.get("job_type") or "").strip()
    tags = [job_type] if job_type else []

    site = str(row.get("site") or "jobspy").lower()

    return {
        "source": site,
        "title": title,
        "company": company,
        "job_url": job_url,
        "location": location,
        "remote_type": remote_type,
        "salary_raw": salary_raw,
        "salary_min_usd": salary_min_usd,
        "salary_max_usd": salary_max_usd,
        "posted_at": posted_at,
        "apply_url": job_url,
        "external_id": str(row.get("id") or "").strip() or None,
        "description": description,
        "tags": tags,
        "metadata": {
            "jobspy_interval": interval or None,
            "jobspy_currency": currency or None,
            "jobspy_salary_source": row.get("salary_source") or None,
        },
    }


def _scrape_once(
    site_name: str,
    search_term: str | None,
    location: str | None,
    results_wanted: int,
    hours_old: int | None,
) -> list[dict[str, Any]]:
    """Single scrape_jobs call with error handling."""
    try:
        # Glassdoor can't parse free-text locations; skip it to avoid 400 errors
        loc = None if site_name.lower() == "glassdoor" else location
        jobs_df = scrape_jobs(
            site_name=[site_name],
            search_term=search_term,
            location=loc,
            results_wanted=results_wanted,
            hours_old=hours_old,
        )
    except Exception:
        return []

    if jobs_df is None or getattr(jobs_df, "empty", True):
        return []

    results: list[dict[str, Any]] = []
    for row in jobs_df.to_dict("records"):
        mapped = _map_jobspy_row(row)
        if mapped is not None:
            results.append(mapped)
    return results


def _shard_search_term(search_term: str | None) -> list[str]:
    """Split a long search term into keyword shards."""
    if not search_term:
        return [""]

    # Split on commas or spaces
    keywords = [
        k.strip() for k in search_term.replace(",", " ").split() if k.strip()
    ]
    if len(keywords) <= _MAX_KEYWORDS_PER_SHARD:
        return [search_term]

    shards: list[str] = []
    for i in range(0, len(keywords), _MAX_KEYWORDS_PER_SHARD):
        shard = keywords[i : i + _MAX_KEYWORDS_PER_SHARD]
        shards.append(" ".join(shard))
    return shards


def _collect_jobspy_for_site(
    site_name: str,
    search_term: str | None = None,
    location: str | None = None,
    results_wanted: int = _DEFAULT_RESULTS_WANTED,
    hours_old: int | None = _DEFAULT_HOURS_OLD,
) -> list[dict[str, Any]]:
    """Fetch jobs from a single JobSpy-supported site.

    Long search terms are automatically sharded into smaller queries so that
    every keyword is searched without overwhelming the target site.
    """
    shards = _shard_search_term(search_term)

    # If there's only one shard, run it directly
    if len(shards) == 1:
        return _scrape_once(
            site_name, shards[0], location, results_wanted, hours_old
        )

    # Multiple shards — run each and deduplicate by job_url
    all_results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for shard_term in shards:
        results = _scrape_once(
            site_name, shard_term, location, results_wanted, hours_old
        )
        for job in results:
            url = job.get("job_url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(job)

    return all_results


def collect_linkedin_jobs(
    search_term: str | None = None,
    location: str | None = None,
    results_wanted: int = _DEFAULT_RESULTS_WANTED,
    hours_old: int | None = _DEFAULT_HOURS_OLD,
) -> list[dict[str, Any]]:
    """Fetch jobs from LinkedIn via JobSpy."""
    return _collect_jobspy_for_site(
        "linkedin",
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )


def collect_indeed_jobs(
    search_term: str | None = None,
    location: str | None = None,
    results_wanted: int = _DEFAULT_RESULTS_WANTED,
    hours_old: int | None = _DEFAULT_HOURS_OLD,
) -> list[dict[str, Any]]:
    """Fetch jobs from Indeed via JobSpy."""
    return _collect_jobspy_for_site(
        "indeed",
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )


def collect_glassdoor_jobs(
    search_term: str | None = None,
    location: str | None = None,
    results_wanted: int = _DEFAULT_RESULTS_WANTED,
    hours_old: int | None = _DEFAULT_HOURS_OLD,
) -> list[dict[str, Any]]:
    """Fetch jobs from Glassdoor via JobSpy."""
    return _collect_jobspy_for_site(
        "glassdoor",
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )
