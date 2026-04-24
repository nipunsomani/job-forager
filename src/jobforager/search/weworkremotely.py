"""We Work Remotely RSS collector for job listings."""

from __future__ import annotations

import ssl
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/rss+xml,application/xml",
    "Referer": "https://weworkremotely.com/",
}


DEFAULT_WWR_URL = "https://weworkremotely.com/remote-jobs.rss"


def collect_weworkremotely_jobs() -> list[dict[str, Any]]:
    """
    Fetch jobs from the We Work Remotely RSS feed.

    Returns:
        List of raw job record dictionaries. Each dict contains:
        - source: "weworkremotely"
        - title: Job title (company prefix stripped if present)
        - company: Company name (extracted from title or None)
        - job_url: URL to the job posting
        - location: None (not provided in RSS)
        - remote_type: "remote" (all We Work Remotely jobs are remote)
        - salary_raw: None
        - salary_min_usd: None
        - salary_max_usd: None
        - posted_at: Publication date string (or None)
        - apply_url: None
        - external_id: None
        - description: Job description (or None)
        - tags: List of category tags (or empty list)
        - metadata: {}

        Returns an empty list if the request fails or the feed
        has no items.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(DEFAULT_WWR_URL, headers=_DEFAULT_HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            raw = response.read()
            charset = response.info().get_content_charset("utf-8")
            xml_text = raw.decode(charset)
    except Exception:
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    # RSS 2.0 channel items
    channel = root.find("channel")
    if channel is None:
        # Try to find items directly if namespace-less
        items = root.findall(".//item")
    else:
        items = channel.findall("item")

    results: list[dict[str, Any]] = []

    for item in items:
        title_elem = item.find("title")
        link_elem = item.find("link")
        pub_date_elem = item.find("pubDate")
        description_elem = item.find("description")

        title = _text_or_none(title_elem)
        link = _text_or_none(link_elem)
        pub_date = _text_or_none(pub_date_elem)
        description = _text_or_none(description_elem)

        company: str | None = None
        job_title = title
        if title and ": " in title:
            parts = title.split(": ", 1)
            if len(parts) == 2:
                company = parts[0].strip() or None
                job_title = parts[1].strip() or None

        tags: list[str] = []
        for category in item.findall("category"):
            cat_text = _text_or_none(category)
            if cat_text:
                tags.append(cat_text)

        raw_record: dict[str, Any] = {
            "source": "weworkremotely",
            "title": job_title,
            "company": company,
            "job_url": link,
            "location": None,
            "remote_type": "remote",
            "salary_raw": None,
            "salary_min_usd": None,
            "salary_max_usd": None,
            "posted_at": pub_date,
            "apply_url": None,
            "external_id": None,
            "description": description,
            "tags": tags,
            "metadata": {},
        }
        results.append(raw_record)

    return results


def _text_or_none(elem: ET.Element | None) -> str | None:
    """Return stripped text of an XML element or None."""
    if elem is None:
        return None
    text = elem.text
    if isinstance(text, str):
        stripped = text.strip()
        return stripped or None
    return None
