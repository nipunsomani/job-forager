"""Personio XML feed collector for job listings.

Fetches open positions from Personio-powered career sites via their
public, unauthenticated XML feed endpoint.
"""

from __future__ import annotations

import ssl
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/xml",
}

from jobforager.company_lists import get_personio_subdomains

_DEFAULT_SUBDOMAINS = get_personio_subdomains()

_PERSONIO_FEED_URL = "https://{subdomain}.jobs.personio.de/xml"


def _fetch_personio_company(subdomain: str) -> list[dict[str, Any]]:
    """Fetch jobs for a single Personio subdomain."""
    url = _PERSONIO_FEED_URL.format(subdomain=subdomain)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            raw = response.read()
            charset = response.info().get_content_charset("utf-8")
            text = raw.decode(charset)
    except Exception:
        return []

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []

    results: list[dict[str, Any]] = []
    ns = {"": "https://www.workzag.com/jobs"}

    # Try with namespace first, then without
    positions = root.findall(".//position", ns)
    if not positions:
        positions = root.findall(".//position")

    for pos in positions:
        job_id = _find_text(pos, "id", ns)
        title = _find_text(pos, "name", ns)
        if not title:
            continue

        office = _find_text(pos, "office", ns)
        additional_offices = []
        add_offices_elem = pos.find("additionalOffices", ns)
        if add_offices_elem is None:
            add_offices_elem = pos.find("additionalOffices")
        if add_offices_elem is not None:
            for off in add_offices_elem.findall("office", ns):
                if off.text:
                    additional_offices.append(off.text.strip())
            if not additional_offices:
                for off in add_offices_elem.findall("office"):
                    if off.text:
                        additional_offices.append(off.text.strip())

        location = office
        if additional_offices:
            location = f"{office}, {', '.join(additional_offices)}" if office else ", ".join(additional_offices)

        company = _find_text(pos, "subcompany", ns) or subdomain
        department = _find_text(pos, "department", ns)
        employment_type = _find_text(pos, "employmentType", ns)
        seniority = _find_text(pos, "seniority", ns)
        schedule = _find_text(pos, "schedule", ns)
        created_at = _find_text(pos, "createdAt", ns)

        # Build job URL
        job_url = None
        if job_id:
            job_url = f"https://{subdomain}.jobs.personio.de/job/{job_id}"

        # Extract description from jobDescriptions
        descriptions: list[str] = []
        job_descs = pos.find("jobDescriptions", ns)
        if job_descs is None:
            job_descs = pos.find("jobDescriptions")
        if job_descs is not None:
            for jd in job_descs.findall("jobDescription", ns):
                desc_name = _find_text(jd, "name", ns)
                desc_value = _find_text(jd, "value", ns)
                if desc_value:
                    if desc_name:
                        descriptions.append(f"{desc_name}: {desc_value}")
                    else:
                        descriptions.append(desc_value)
            if not descriptions:
                for jd in job_descs.findall("jobDescription"):
                    desc_name = _find_text(jd, "name", ns)
                    desc_value = _find_text(jd, "value", ns)
                    if desc_value:
                        if desc_name:
                            descriptions.append(f"{desc_name}: {desc_value}")
                        else:
                            descriptions.append(desc_value)

        description = "\n\n".join(descriptions) if descriptions else None

        # Tags from keywords
        tags: list[str] = []
        keywords = _find_text(pos, "keywords", ns)
        if keywords:
            tags = [k.strip() for k in keywords.split(",") if k.strip()]

        # Determine remote type
        remote_type = None
        if employment_type and "remote" in employment_type.lower():
            remote_type = "remote"

        raw_record: dict[str, Any] = {
            "source": "personio",
            "title": title,
            "company": company,
            "job_url": job_url,
            "location": location or None,
            "remote_type": remote_type,
            "salary_raw": None,
            "salary_min_usd": None,
            "salary_max_usd": None,
            "posted_at": created_at,
            "apply_url": None,
            "external_id": job_id,
            "description": description,
            "tags": tags,
            "metadata": {
                "subdomain": subdomain,
                "department": department,
                "employment_type": employment_type,
                "seniority": seniority,
                "schedule": schedule,
            },
        }
        results.append(raw_record)

    return results


def _find_text(elem: ET.Element, tag: str, ns: dict[str, str]) -> str | None:
    """Find child element text with namespace fallback."""
    child = elem.find(tag, ns)
    if child is None:
        child = elem.find(tag)
    if child is not None and child.text:
        return child.text.strip() or None
    return None


def collect_personio_jobs(
    subdomains: list[str] | None = None,
    max_workers: int = 10,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from Personio-powered career sites.

    Args:
        subdomains: List of Personio subdomains to query.
            Defaults to a curated list if not provided.
        max_workers: Number of concurrent threads.

    Returns:
        List of raw job record dictionaries.
    """
    targets = subdomains if subdomains is not None else _DEFAULT_SUBDOMAINS

    if max_workers <= 1:
        all_results: list[dict[str, Any]] = []
        for subdomain in targets:
            jobs = _fetch_personio_company(subdomain)
            all_results.extend(jobs)
        return all_results

    all_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_personio_company, subdomain): subdomain
            for subdomain in targets
        }
        for future in as_completed(futures):
            try:
                jobs = future.result()
                all_results.extend(jobs)
            except Exception:
                pass

    return all_results
