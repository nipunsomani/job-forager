"""Remotive API collector for job listings."""

import html
import json
import re
import ssl
import urllib.request
from typing import Any


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Referer": "https://remotive.com/",
    "Accept": "application/json",
}


def strip_html_tags(text: str) -> str:
    """
    Strip HTML tags from text and format it cleanly.

    Args:
        text: Raw HTML text string.

    Returns:
        Cleaned text with HTML tags removed and whitespace normalized.
    """
    if not text:
        return ""

    # Decode HTML entities
    text = html.unescape(text)

    # Remove script and style tags and their contents
    text = re.sub(
        r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(
        r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE
    )

    # Replace block-level tags with newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li\s*>", "\n• ", text, flags=re.IGNORECASE)

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t\r]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)

    return text.strip()


def collect_remotive_jobs(
    category: str = "software-dev", limit: int = 999
) -> list[dict[str, Any]]:
    """
    Fetch jobs from the Remotive API.

    Args:
        category: The job category to fetch (e.g., "software-dev").
            Defaults to "software-dev".
        limit: Maximum number of jobs to fetch. Defaults to 999 (get all available).

    Returns:
        List of raw job record dictionaries. Each dict contains:
        - source: "remotive"
        - title: Job title (stripped)
        - company: Company name (stripped)
        - job_url: URL to the job posting
        - location: Candidate required location (or None)
        - remote_type: "remote" (all Remotive jobs are remote)
        - salary_raw: Raw salary string (or None)
        - salary_min_usd: None (salary field is free text)
        - salary_max_usd: None
        - posted_at: Publication date as ISO-8601 string
        - apply_url: None
        - external_id: Job ID as string (or None)
        - description: HTML description with tags stripped
        - tags: List of tags (or empty list)
        - metadata: {"category": category}

        Returns an empty list if the request fails or the response
        has no jobs.
    """
    url = f"https://remotive.com/api/remote-jobs?category={category}&limit={limit}"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            raw = response.read()
            charset = response.info().get_content_charset("utf-8")
            data = json.loads(raw.decode(charset))
    except Exception:
        return []

    jobs = data.get("jobs", [])
    if not jobs:
        return []

    results: list[dict[str, Any]] = []

    for job in jobs:
        raw_record: dict[str, Any] = {
            "source": "remotive",
            "title": job.get("title", "").strip(),
            "company": job.get("company_name", "").strip(),
            "job_url": job.get("url", "").strip() or None,
            "location": job.get("candidate_required_location", "").strip() or None,
            "remote_type": "remote",
            "salary_raw": job.get("salary", "").strip() or None,
            "salary_min_usd": None,
            "salary_max_usd": None,
            "posted_at": job.get("publication_date", "") or None,
            "apply_url": None,
            "external_id": str(job.get("id", "")) or None,
            "description": strip_html_tags(job.get("description", "")),
            "tags": job.get("tags", []) or [],
            "metadata": {"category": category},
        }
        results.append(raw_record)

    return results
