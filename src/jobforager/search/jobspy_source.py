"""JobSpy collector for LinkedIn, Indeed, and Glassdoor.

This module wraps the ``python-jobspy`` package to scrape major job boards.
"""

from __future__ import annotations

from typing import Any

from jobspy import scrape_jobs

_DEFAULT_SEARCH_TERM = ""
_DEFAULT_RESULTS_WANTED = 50
_DEFAULT_HOURS_OLD = 168  # 7 days


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

    # Salary handling
    min_amount = row.get("min_amount")
    max_amount = row.get("max_amount")
    currency = str(row.get("currency") or "").strip().upper()
    interval = str(row.get("interval") or "").strip().lower()

    salary_raw = None
    if min_amount is not None or max_amount is not None:
        parts: list[str] = []
        if min_amount is not None:
            parts.append(str(min_amount))
        if max_amount is not None:
            parts.append(str(max_amount))
        if interval:
            parts.append(interval)
        if currency:
            parts.append(currency)
        salary_raw = " - ".join(parts)

    salary_min_usd = None
    salary_max_usd = None
    if currency == "USD" and min_amount is not None:
        salary_min_usd = int(min_amount)
    if currency == "USD" and max_amount is not None:
        salary_max_usd = int(max_amount)

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


def _collect_jobspy_for_site(
    site_name: str,
    search_term: str | None = None,
    location: str | None = None,
    results_wanted: int = _DEFAULT_RESULTS_WANTED,
    hours_old: int | None = _DEFAULT_HOURS_OLD,
) -> list[dict[str, Any]]:
    """Fetch jobs from a single JobSpy-supported site."""
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
