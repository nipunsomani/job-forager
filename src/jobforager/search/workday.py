"""Workday job board API collector for job listings.

Uses the reverse-engineered Workday Calypso API to fetch jobs from
Workday-powered career sites. Requires a CSRF token obtained from the
career site homepage.
"""

import json
import re
import ssl
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/json",
}

from jobforager.company_lists import get_workday_companies

_DEFAULT_COMPANIES = get_workday_companies()

_PAGE_SIZE = 20


def _parse_workday_url(career_site_url: str) -> dict[str, str]:
    """Parse a Workday career site URL into API components."""
    url = career_site_url.rstrip("/")
    match = re.match(r"https://([^/]+)/(.+)", url)
    if not match:
        raise ValueError(f"Invalid Workday URL: {career_site_url}")

    domain = match.group(1)
    path = match.group(2)

    # Handle myworkdaysite.com/recruiting/{company}/{site} format
    recruiting_match = re.match(r"recruiting/([^/]+)/(.+)", path)
    if recruiting_match:
        company_name = recruiting_match.group(1)
        site_name = recruiting_match.group(2)
    else:
        company_match = re.match(r"^([^.]+)\.", domain)
        if not company_match:
            raise ValueError(f"Could not extract company from domain: {domain}")
        company_name = company_match.group(1)
        site_name = path.split("/")[-1] or path

    api_base_url = f"https://{domain}/wday/cxs/{company_name}/{site_name}"

    return {
        "domain": domain,
        "company_name": company_name,
        "site_name": site_name,
        "api_base_url": api_base_url,
        "career_site_url": url,
    }


def _get_csrf_token(career_site_url: str) -> str | None:
    """Fetch the Workday career page and extract the CSRF token."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(
            career_site_url,
            headers={
                **_DEFAULT_HEADERS,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                ),
            },
        )
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            csrf = response.headers.get("x-calypso-csrf-token")
            if csrf:
                return csrf
    except Exception:
        pass

    return None


def _fetch_workday_company(
    company_info: dict[str, str],
    max_results: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch jobs for a single Workday-powered company."""
    try:
        parsed = _parse_workday_url(company_info["url"])
    except ValueError:
        return []

    career_site_url = parsed["career_site_url"]
    api_base_url = parsed["api_base_url"]
    company_name = company_info.get("name") or parsed["company_name"]

    csrf_token = _get_csrf_token(career_site_url)
    if not csrf_token:
        return []

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    all_jobs: list[dict[str, Any]] = []
    offset = 0
    total_available: int | None = None

    while True:
        if max_results is not None and len(all_jobs) >= max_results:
            break

        if total_available is not None and len(all_jobs) >= total_available:
            break

        payload = {
            "appliedFacets": {},
            "limit": _PAGE_SIZE,
            "offset": offset,
            "searchText": "",
        }

        api_url = f"{api_base_url}/jobs"

        try:
            req = urllib.request.Request(
                api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    **_DEFAULT_HEADERS,
                    "Content-Type": "application/json",
                    "Origin": f"https://{parsed['domain']}",
                    "Referer": career_site_url,
                    "x-calypso-csrf-token": csrf_token,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
                raw = response.read()
                charset = response.info().get_content_charset("utf-8")
                data = json.loads(raw.decode(charset))
        except Exception:
            break

        if not isinstance(data, dict):
            break

        job_postings = data.get("jobPostings", [])
        if not isinstance(job_postings, list):
            break

        if total_available is None:
            total_available = data.get("total", len(job_postings))

        if not job_postings:
            break

        all_jobs.extend(job_postings)
        offset += _PAGE_SIZE

    results: list[dict[str, Any]] = []
    for job in all_jobs:
        if not isinstance(job, dict):
            continue

        title = _extract_string(job, "title")
        if not title:
            # Skip jobs with missing titles to avoid normalization errors
            continue

        bullet_fields = job.get("bulletFields", []) or []
        job_id = bullet_fields[0] if bullet_fields else ""
        location = bullet_fields[1] if len(bullet_fields) > 1 else ""

        external_path = job.get("externalPath", "")
        job_url = None
        if external_path:
            if external_path.startswith("http"):
                job_url = external_path
            else:
                job_url = f"{career_site_url}{external_path}"

        raw_record: dict[str, Any] = {
            "source": "workday",
            "title": title,
            "company": company_name,
            "job_url": job_url,
            "location": location or None,
            "remote_type": None,
            "salary_raw": None,
            "salary_min_usd": None,
            "salary_max_usd": None,
            "posted_at": _extract_string(job, "postedOn"),
            "apply_url": None,
            "external_id": job_id or None,
            "description": None,
            "tags": [],
            "metadata": {
                "career_site_url": career_site_url,
                "external_path": external_path,
                "bullet_fields": bullet_fields,
            },
        }
        results.append(raw_record)

    return results


def collect_workday_jobs(
    companies: list[dict[str, str]] | None = None,
    max_results_per_company: int | None = None,
    delay: float = 0.5,
    max_companies: int | None = None,
    max_workers: int = 10,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from Workday-powered career sites.

    Args:
        companies: List of company dicts with "name" and "url" keys.
            Defaults to a curated list if not provided.
        max_results_per_company: Maximum jobs to fetch per company.
        delay: Seconds to sleep between company requests (sequential mode only).
        max_companies: Maximum number of companies to query. None = all available.
        max_workers: Number of concurrent threads. >1 enables parallel fetching.

    Returns:
        List of raw job record dictionaries. Returns an empty list if
        all requests fail or no jobs are found.
    """
    comps = companies if companies is not None else _DEFAULT_COMPANIES
    if max_companies is not None and max_companies > 0:
        comps = comps[:max_companies]

    if max_workers <= 1:
        all_results: list[dict[str, Any]] = []
        for company in comps:
            company_jobs = _fetch_workday_company(
                company, max_results=max_results_per_company
            )
            all_results.extend(company_jobs)
            if delay and len(comps) > 1:
                time.sleep(delay)
        return all_results

    all_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_workday_company, company, max_results_per_company): company
            for company in comps
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
