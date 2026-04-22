"""RemoteOK API collector for job listings."""

import json
import ssl
import urllib.request
from typing import Any


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/json",
    "Referer": "https://remoteok.com/",
}


DEFAULT_REMOTEOK_URL = "https://remoteok.com/api"


def collect_remoteok_jobs(tag: str | None = None) -> list[dict[str, Any]]:
    """
    Fetch jobs from the RemoteOK API.

    Args:
        tag: Optional job tag to filter by (e.g., "python", "devops").

    Returns:
        List of raw job record dictionaries. Each dict contains:
        - source: "remoteok"
        - title: Job title
        - company: Company name
        - job_url: URL to the job posting
        - location: Location string (or None)
        - remote_type: "remote" (all RemoteOK jobs are remote)
        - salary_raw: Raw salary string (or None)
        - salary_min_usd: None
        - salary_max_usd: None
        - posted_at: Publication date as ISO-8601 string (or None)
        - apply_url: Application URL (or None)
        - external_id: Job ID as string (or None)
        - description: Job description (or None)
        - tags: List of tags (or empty list)
        - metadata: {"tag": tag} if tag was provided

        Returns an empty list if the request fails or the response
        has no jobs.
    """
    url = DEFAULT_REMOTEOK_URL
    if tag:
        url = f"{url}?tag={urllib.parse.quote(tag)}"

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

    for item in data:
        if not isinstance(item, dict):
            continue
        is_metadata = "id" not in item or item.get("legal") is not None
        if is_metadata:
            continue

        raw_record: dict[str, Any] = {
            "source": "remoteok",
            "title": _extract_string(item, "position"),
            "company": _extract_string(item, "company"),
            "job_url": _extract_url(item, "url"),
            "location": _extract_string(item, "location"),
            "remote_type": "remote",
            "salary_raw": _extract_string(item, "salary") or None,
            "salary_min_usd": None,
            "salary_max_usd": None,
            "posted_at": _extract_string(item, "date") or None,
            "apply_url": _extract_url(item, "apply_url"),
            "external_id": str(item.get("id", "")) or None,
            "description": _extract_string(item, "description"),
            "tags": _extract_tags(item.get("tags")),
            "metadata": {"tag": tag} if tag else {},
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
