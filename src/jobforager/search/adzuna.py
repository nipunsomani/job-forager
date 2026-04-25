"""Adzuna API collector for job listings."""

from __future__ import annotations

import json
import os
import ssl
import urllib.parse
import urllib.request
from typing import Any


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/json",
    "Referer": "https://www.adzuna.com/",
}


def collect_adzuna_jobs(
    search_term: str | None = None,
    location: str | None = None,
    country: str = "gb",
    results_per_page: int = 50,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from the Adzuna API.

    Args:
        search_term: Search term / job title keywords.
        location: Location filter.
        country: Two-letter country code (e.g., "gb", "us"). Defaults to "gb".
        results_per_page: Number of results per page. Defaults to 50.

    Returns:
        List of raw job record dictionaries. Each dict contains:
        - source: "adzuna"
        - title: Job title
        - company: Company name
        - job_url: URL to the job posting
        - location: Location string (or None)
        - remote_type: None (Adzuna does not provide this)
        - salary_raw: Formatted salary string (or None)
        - salary_min_usd: Minimum salary in USD (or None)
        - salary_max_usd: Maximum salary in USD (or None)
        - posted_at: Publication date as ISO-8601 string (or None)
        - apply_url: Same as job_url
        - external_id: Job ID as string (or None)
        - description: Job description (or None)
        - tags: List of tags (or empty list)
        - metadata: {"contract_type", "contract_time", "salary_currency"}

        Returns an empty list if credentials are missing or the request fails.
    """
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return []

    params: dict[str, str] = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": str(results_per_page),
    }
    if search_term:
        params["what"] = search_term
    if location:
        params["where"] = location

    query = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in params.items())
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1?{query}"

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

    jobs = data.get("results", []) if isinstance(data, dict) else []
    if not isinstance(jobs, list):
        return []

    results: list[dict[str, Any]] = []

    for job in jobs:
        if not isinstance(job, dict):
            continue

        adzuna_job = job.get("job", {}) if isinstance(job.get("job"), dict) else job

        salary_min = adzuna_job.get("salary_min")
        salary_max = adzuna_job.get("salary_max")
        salary_currency = adzuna_job.get("salary_currency")
        salary_is_predicted = adzuna_job.get("salary_is_predicted")

        salary_raw = None
        if salary_min is not None or salary_max is not None:
            parts: list[str] = []
            if salary_min is not None:
                parts.append(str(salary_min))
            if salary_max is not None:
                parts.append(str(salary_max))
            raw_str = " - ".join(parts)
            if salary_currency:
                raw_str += f" {salary_currency}"
            if salary_is_predicted:
                raw_str += " (predicted)"
            salary_raw = raw_str or None

        salary_min_usd = None
        salary_max_usd = None
        if salary_currency == "USD":
            if isinstance(salary_min, (int, float)):
                salary_min_usd = float(salary_min)
            if isinstance(salary_max, (int, float)):
                salary_max_usd = float(salary_max)

        company_data = adzuna_job.get("company", {}) or {}
        location_data = adzuna_job.get("location", {}) or {}
        category_data = adzuna_job.get("category", {}) or {}

        raw_record: dict[str, Any] = {
            "source": "adzuna",
            "title": _extract_string(adzuna_job, "title"),
            "company": _extract_string(company_data, "display_name"),
            "job_url": _extract_url(adzuna_job, "redirect_url"),
            "location": _extract_string(location_data, "display_name"),
            "remote_type": None,
            "salary_raw": salary_raw,
            "salary_min_usd": salary_min_usd,
            "salary_max_usd": salary_max_usd,
            "posted_at": _extract_string(adzuna_job, "created") or None,
            "apply_url": _extract_url(adzuna_job, "redirect_url"),
            "external_id": str(adzuna_job.get("id", "")) or None,
            "description": _extract_string(adzuna_job, "description"),
            "tags": [_extract_string(category_data, "label")] if category_data.get("label") else [],
            "metadata": {
                "contract_type": adzuna_job.get("contract_type"),
                "contract_time": adzuna_job.get("contract_time"),
                "salary_currency": salary_currency,
            },
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
