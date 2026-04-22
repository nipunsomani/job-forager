"""Lever public postings API collector for job listings."""

import json
import ssl
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/json",
}

from jobforager.company_lists import get_lever_slugs

_DEFAULT_COMPANY_SLUGS = get_lever_slugs()

_LEVER_API_URL = "https://api.lever.co/v0/postings/{company_slug}?mode=json"

_LEVER_WORKPLACE_MAP = {
    "remote": "remote",
    "on-site": "onsite",
    "onsite": "onsite",
    "hybrid": "hybrid",
}


def _fetch_lever_company(company_slug: str) -> list[dict[str, Any]]:
    """Fetch jobs for a single Lever company slug."""
    url = _LEVER_API_URL.format(company_slug=company_slug)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            raw = response.read()
            charset = response.info().get_content_charset("utf-8")
            data = json.loads(raw.decode(charset))
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    results: list[dict[str, Any]] = []
    for job in data:
        if not isinstance(job, dict):
            continue

        categories = job.get("categories", {}) or {}
        location = categories.get("location", "").strip() or None
        commitment = categories.get("commitment", "").strip() or None
        team = categories.get("team", "").strip() or None
        department = categories.get("department", "").strip() or None

        workplace_raw = str(job.get("workplaceType", "")).strip().lower()
        remote_type = _LEVER_WORKPLACE_MAP.get(workplace_raw)

        salary_raw = None
        salary_min = None
        salary_max = None
        salary_range = job.get("salaryRange")
        if isinstance(salary_range, dict):
            salary_min = salary_range.get("min")
            salary_max = salary_range.get("max")
            if salary_min is not None and salary_max is not None:
                currency = salary_range.get("currency", "USD")
                interval = salary_range.get("interval", "yearly")
                salary_raw = f"{currency} {salary_min}-{salary_max} / {interval}"

        posted_at = None
        created_at = job.get("createdAt")
        if isinstance(created_at, (int, float)):
            try:
                posted_at = datetime.fromtimestamp(
                    created_at / 1000, tz=timezone.utc
                ).isoformat()
            except (ValueError, OSError, OverflowError):
                posted_at = None

        tags: list[str] = []
        if department:
            tags.append(department)
        if team:
            tags.append(team)
        if commitment:
            tags.append(commitment)

        raw_record: dict[str, Any] = {
            "source": "lever",
            "title": _extract_string(job, "text"),
            "company": company_slug,
            "job_url": _extract_url(job, "hostedUrl"),
            "location": location,
            "remote_type": remote_type,
            "salary_raw": salary_raw,
            "salary_min_usd": salary_min if isinstance(salary_min, int) else None,
            "salary_max_usd": salary_max if isinstance(salary_max, int) else None,
            "posted_at": posted_at,
            "apply_url": _extract_url(job, "applyUrl"),
            "external_id": _extract_string(job, "id"),
            "description": _extract_string(job, "descriptionPlain")
            or _extract_string(job, "openingPlain"),
            "tags": tags,
            "metadata": {
                "company_slug": company_slug,
                "commitment": commitment,
                "country": job.get("country"),
            },
        }
        results.append(raw_record)

    return results


def collect_lever_jobs(
    company_slugs: list[str] | None = None,
    delay: float = 0.1,
    max_companies: int | None = None,
    max_workers: int = 30,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from the Lever public postings API.

    Args:
        company_slugs: List of Lever company slugs (e.g., ["airbnb", "netflix"]).
            Defaults to a curated list if not provided.
        delay: Seconds to sleep between company requests (sequential mode only).
        max_companies: Maximum number of companies to query. None = all available.
        max_workers: Number of concurrent threads. >1 enables parallel fetching.

    Returns:
        List of raw job record dictionaries. Returns an empty list if
        all requests fail or no jobs are found.
    """
    slugs = company_slugs if company_slugs is not None else _DEFAULT_COMPANY_SLUGS
    if max_companies is not None and max_companies > 0:
        slugs = slugs[:max_companies]

    if max_workers <= 1:
        all_results: list[dict[str, Any]] = []
        for slug in slugs:
            company_jobs = _fetch_lever_company(slug)
            all_results.extend(company_jobs)
            if delay and len(slugs) > 1:
                time.sleep(delay)
        return all_results

    all_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_lever_company, slug): slug
            for slug in slugs
        }
        for future in as_completed(futures):
            try:
                company_jobs = future.result()
                all_results.extend(company_jobs)
            except Exception:
                pass

    return all_results


def _extract_string(data: dict[str, Any], key: str) -> str | None:
    """Extract and strip a string value from a dict."""
    value = data.get(key)
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _extract_url(data: dict[str, Any], key: str) -> str | None:
    """Extract a URL string from a dict, ensuring it is non-empty."""
    value = data.get(key)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped.startswith(("http://", "https://")):
            return stripped
    return None
