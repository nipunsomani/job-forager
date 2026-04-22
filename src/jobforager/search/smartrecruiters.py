"""SmartRecruiters public API collector for job listings."""

import json
import ssl
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/json",
}

from jobforager.company_lists import get_smartrecruiters_slugs

_DEFAULT_COMPANY_SLUGS = get_smartrecruiters_slugs()

_SMARTRECRUITERS_API_URL = (
    "https://api.smartrecruiters.com/v1/companies/{company_slug}/postings"
)

_PAGE_LIMIT = 100


def _fetch_smartrecruiters_company(company_slug: str) -> list[dict[str, Any]]:
    """Fetch all jobs for a single SmartRecruiters company slug."""
    base_url = _SMARTRECRUITERS_API_URL.format(company_slug=company_slug)
    all_content: list[dict[str, Any]] = []
    offset = 0
    total_found: int | None = None

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    while True:
        url = f"{base_url}?limit={_PAGE_LIMIT}&offset={offset}"

        try:
            req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
            with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
                raw = response.read()
                charset = response.info().get_content_charset("utf-8")
                data = json.loads(raw.decode(charset))
        except Exception:
            break

        if not isinstance(data, dict):
            break

        content = data.get("content", [])
        if not isinstance(content, list):
            break

        if total_found is None:
            total_found = data.get("totalFound", len(content))

        all_content.extend(content)

        if len(content) == 0 or len(content) < _PAGE_LIMIT or len(all_content) >= total_found:
            break

        offset += _PAGE_LIMIT

    results: list[dict[str, Any]] = []
    for job in all_content:
        if not isinstance(job, dict):
            continue

        company_name = None
        company = job.get("company")
        if isinstance(company, dict):
            company_name = company.get("name", "").strip() or None

        location_parts: list[str] = []
        location = job.get("location")
        if isinstance(location, dict):
            city = location.get("city", "").strip()
            country = location.get("country", "").strip()
            if city:
                location_parts.append(city)
            if country:
                location_parts.append(country)
        location_str = ", ".join(location_parts) if location_parts else None

        description = None
        job_ad = job.get("jobAd")
        if isinstance(job_ad, dict):
            sections = job_ad.get("sections", {})
            if isinstance(sections, dict):
                desc_section = sections.get("jobDescription")
                if isinstance(desc_section, dict):
                    description = desc_section.get("text", "").strip() or None

        tags: list[str] = []
        employment = job.get("typeOfEmployment")
        if isinstance(employment, dict):
            label = employment.get("label", "").strip()
            if label:
                tags.append(label)

        job_url = _extract_url(job, "postingUrl")
        if not job_url:
            job_id = _extract_string(job, "id")
            if job_id:
                job_url = f"https://jobs.smartrecruiters.com/{company_slug}/{job_id}"

        raw_record: dict[str, Any] = {
            "source": "smartrecruiters",
            "title": _extract_string(job, "name"),
            "company": company_name or company_slug,
            "job_url": job_url,
            "location": location_str,
            "remote_type": None,
            "salary_raw": None,
            "salary_min_usd": None,
            "salary_max_usd": None,
            "posted_at": _extract_string(job, "createdOn"),
            "apply_url": None,
            "external_id": _extract_string(job, "id"),
            "description": description,
            "tags": tags,
            "metadata": {
                "company_slug": company_slug,
                "ref_number": _extract_string(job, "refNumber"),
            },
        }
        results.append(raw_record)

    return results


def collect_smartrecruiters_jobs(
    company_slugs: list[str] | None = None,
    delay: float = 0.1,
    max_workers: int = 10,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from the SmartRecruiters public API.

    Args:
        company_slugs: List of company slugs (e.g., ["adobe1", "canva"]).
            Defaults to a curated list if not provided.
        delay: Seconds to sleep between company requests (sequential mode only).
        max_workers: Number of concurrent threads. >1 enables parallel fetching.

    Returns:
        List of raw job record dictionaries. Returns an empty list if
        all requests fail or no jobs are found.
    """
    slugs = company_slugs if company_slugs is not None else _DEFAULT_COMPANY_SLUGS

    if max_workers <= 1:
        all_results: list[dict[str, Any]] = []
        for slug in slugs:
            company_jobs = _fetch_smartrecruiters_company(slug)
            all_results.extend(company_jobs)
            if delay and len(slugs) > 1:
                time.sleep(delay)
        return all_results

    all_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_smartrecruiters_company, slug): slug
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
