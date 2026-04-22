"""Hacker News "Who's Hiring" collector via Firebase API."""

import calendar
import html
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/json",
}

_HN_ALGOLIA_SEARCH_URL = (
    "https://hn.algolia.com/api/v1/search"
    "?query={query}&tags=story&numericFilters=created_at_i>{start},created_at_i<{end}"
)
_HN_FIREBASE_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"

_URL_RE = re.compile(r"https?://[^\s<>\"]+")


def _month_bounds(year: int, month: int) -> tuple[int, int]:
    first_day = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    last_day_num = calendar.monthrange(year, month)[1]
    last_day = datetime(year, month, last_day_num, 23, 59, 59, tzinfo=timezone.utc)
    return int(first_day.timestamp()), int(last_day.timestamp())


def find_hn_whos_hiring_thread(year: int, month: int) -> int | None:
    """Find the HN "Who is hiring?" thread ID for a given month using Algolia."""
    start_unix, end_unix = _month_bounds(year, month)
    query = "Ask HN: Who is hiring?"
    url = _HN_ALGOLIA_SEARCH_URL.format(
        query=urllib.parse.quote(query),
        start=start_unix,
        end=end_unix,
    )

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
        return None

    hits = data.get("hits", [])
    if not hits:
        return None

    object_id = hits[0].get("objectID")
    if object_id is None:
        return None

    try:
        return int(object_id)
    except (ValueError, TypeError):
        return None


def fetch_hn_item(item_id: int) -> dict[str, Any] | None:
    """Fetch a single HN item from the Firebase API."""
    url = _HN_FIREBASE_ITEM_URL.format(item_id=item_id)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            raw = response.read()
            charset = response.info().get_content_charset("utf-8")
            return json.loads(raw.decode(charset))
    except Exception:
        return None


def parse_hn_job_comment(comment: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a HN comment dict into a raw job record dict."""
    text = comment.get("text")
    if not text:
        return None

    text = html.unescape(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    first_line = lines[0]
    description = "\n".join(lines[1:]) if len(lines) > 1 else ""

    segments = [seg.strip() for seg in first_line.split("|")]
    if len(segments) >= 2:
        company = segments[0] or "Unknown Company"
        title = segments[1] or "Unknown Role"
        location = segments[2] if len(segments) >= 3 else None
        remote_raw = segments[3].lower() if len(segments) >= 4 else ""
        salary_raw = segments[4] if len(segments) >= 5 else None

        if remote_raw in ("yes", "remote"):
            remote_type = "remote"
        elif remote_raw == "no":
            remote_type = "onsite"
        elif remote_raw == "hybrid":
            remote_type = "hybrid"
        else:
            remote_type = None
    else:
        company = "Unknown Company"
        title = first_line or "Unknown Role"
        location = None
        remote_type = None
        salary_raw = None
        description = text

    urls = _URL_RE.findall(text)
    job_url = urls[0] if urls else None
    apply_url = job_url

    posted_at: str | None = None
    if "time" in comment:
        try:
            posted_at = datetime.fromtimestamp(
                comment["time"], tz=timezone.utc
            ).isoformat()
        except (ValueError, TypeError, OverflowError):
            posted_at = None

    return {
        "source": "hackernews",
        "title": title,
        "company": company,
        "job_url": job_url,
        "location": location,
        "remote_type": remote_type,
        "salary_raw": salary_raw,
        "salary_min_usd": None,
        "salary_max_usd": None,
        "posted_at": posted_at,
        "apply_url": apply_url,
        "external_id": str(comment.get("id", "")) or None,
        "description": description.strip(),
        "tags": ["hackernews"],
        "metadata": {
            "hn_parent": comment.get("parent"),
            "hn_by": comment.get("by"),
        },
    }


def collect_hackernews_jobs(
    year: int | None = None,
    month: int | None = None,
    max_comments: int = 50,
    delay: float = 0.5,
) -> list[dict[str, Any]]:
    """Collect job postings from the HN "Who's Hiring?" thread."""
    if year is None or month is None:
        now = datetime.now(timezone.utc)
        year = year or now.year
        month = month or now.month

    try:
        thread_id = find_hn_whos_hiring_thread(year, month)
        if thread_id is None:
            return []

        thread = fetch_hn_item(thread_id)
        if thread is None:
            return []

        kids = thread.get("kids", [])
        if not kids:
            return []

        results: list[dict[str, Any]] = []
        for kid_id in kids[:max_comments]:
            comment = fetch_hn_item(kid_id)
            if comment is not None:
                parsed = parse_hn_job_comment(comment)
                if parsed is not None:
                    results.append(parsed)
            time.sleep(delay)

        return results
    except Exception:
        return []
