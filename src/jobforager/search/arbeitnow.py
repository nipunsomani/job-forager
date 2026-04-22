"""ArbeitNow API collector for job listings."""

import json
import ssl
import urllib.request
from typing import Any


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/json",
    "Referer": "https://arbeitnow.com/",
}


DEFAULT_ARBEITNOW_URL = "https://arbeitnow.com/api/job-board-api"


def collect_arbeitnow_jobs() -> list[dict[str, Any]]:
    """
    Fetch jobs from the ArbeitNow API.

    Returns:
        List of raw job record dictionaries. Each dict contains:
        - source: "arbeitnow"
        - title: Job title
        - company: Company name
        - job_url: URL to the job posting
        - location: Location string (or None)
        - remote_type: "remote" if remote is True, else None
        - salary_raw: None (API does not provide salary)
        - salary_min_usd: None
        - salary_max_usd: None
        - posted_at: Publication date as ISO-8601 string (or None)
        - apply_url: None (use job_url)
        - external_id: Job slug as string (or None)
        - description: Job description (or None)
        - tags: List of tags (or empty list)
        - metadata: {}

        Returns an empty list if the request fails or the response
        has no jobs.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(DEFAULT_ARBEITNOW_URL, headers=_DEFAULT_HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            raw = response.read()
            charset = response.info().get_content_charset("utf-8")
            data = json.loads(raw.decode(charset))
    except Exception:
        return []

    jobs = data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []

    results: list[dict[str, Any]] = []

    for job in jobs:
        if not isinstance(job, dict):
            continue

        remote_type = None
        if job.get("remote") is True:
            remote_type = "remote"

        raw_record: dict[str, Any] = {
            "source": "arbeitnow",
            "title": _extract_string(job, "title"),
            "company": _extract_string(job, "company_name"),
            "job_url": _extract_url(job, "url"),
            "location": _extract_string(job, "location"),
            "remote_type": remote_type,
            "salary_raw": None,
            "salary_min_usd": None,
            "salary_max_usd": None,
            "posted_at": _extract_string(job, "date") or None,
            "apply_url": None,
            "external_id": _extract_string(job, "slug"),
            "description": _extract_string(job, "description"),
            "tags": _extract_tags(job.get("tags")),
            "metadata": {},
        }
        results.append(raw_record)

    return results


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


def _extract_tags(value: Any) -> list[str]:
    """Normalize tags into a list of strings."""
    if isinstance(value, list):
        tags: list[str] = []
        for item in value:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    tags.append(stripped)
        return tags
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return []
