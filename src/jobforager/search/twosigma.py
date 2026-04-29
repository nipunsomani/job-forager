"""Two Sigma RSS collector for job listings.

Fetches open roles from Two Sigma's Avature-powered RSS feed.
"""

from __future__ import annotations

import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/rss+xml,application/xml",
}

DEFAULT_TWOSIGMA_URL = (
    "https://careers.twosigma.com/careers/OpenRoles/feed/?jobRecordsPerPage=100"
)


def collect_twosigma_jobs() -> list[dict[str, Any]]:
    """
    Fetch jobs from the Two Sigma RSS feed.

    Returns:
        List of raw job record dictionaries. Each dict contains:
        - source: "twosigma"
        - title: Job title
        - company: "Two Sigma"
        - job_url: URL to the job posting
        - location: Location string (or None)
        - remote_type: None
        - salary_raw: None
        - salary_min_usd: None
        - salary_max_usd: None
        - posted_at: Publication date as ISO-8601 string (or None)
        - apply_url: None
        - external_id: Job ID extracted from URL (or None)
        - description: None
        - tags: []
        - metadata: {}

        Returns an empty list if the request fails or the response
        has no items.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(DEFAULT_TWOSIGMA_URL, headers=_DEFAULT_HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            raw = response.read()
            charset = response.info().get_content_charset("utf-8")
            text = raw.decode(charset)
    except Exception:
        return []

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item")

    results: list[dict[str, Any]] = []

    for item in items:
        title_elem = item.find("title")
        title = _strip_cdata(title_elem.text) if title_elem is not None and title_elem.text else None

        desc_elem = item.find("description")
        location = _strip_cdata(desc_elem.text) if desc_elem is not None and desc_elem.text else None

        link_elem = item.find("link")
        job_url = link_elem.text.strip() if link_elem is not None and link_elem.text else None

        pub_elem = item.find("pubDate")
        posted_at = None
        if pub_elem is not None and pub_elem.text:
            posted_at = _parse_rfc822_date(pub_elem.text.strip())

        external_id = None
        if job_url:
            parts = job_url.rstrip("/").split("/")
            if parts:
                external_id = parts[-1]

        raw_record: dict[str, Any] = {
            "source": "twosigma",
            "title": title,
            "company": "Two Sigma",
            "job_url": job_url,
            "location": location,
            "remote_type": None,
            "salary_raw": None,
            "salary_min_usd": None,
            "salary_max_usd": None,
            "posted_at": posted_at,
            "apply_url": None,
            "external_id": external_id,
            "description": None,
            "tags": [],
            "metadata": {},
        }
        results.append(raw_record)

    return results


def _strip_cdata(text: str) -> str | None:
    """Strip CDATA wrapper and whitespace from text."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("<![CDATA[") and cleaned.endswith("]]>"):
        cleaned = cleaned[9:-3].strip()
    return cleaned or None


def _parse_rfc822_date(text: str) -> str | None:
    """Parse an RFC-822 date string to ISO-8601 format."""
    # Example: Wed, 27 Nov 2024 00:00:00 +0000
    try:
        dt = datetime.strptime(text, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        pass
    try:
        dt = datetime.strptime(text, "%a, %d %b %Y %H:%M:%S %Z")
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        pass
    return None
