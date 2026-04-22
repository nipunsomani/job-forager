"""Greenhouse Job Board API collector for job listings."""

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

from jobforager.company_lists import get_greenhouse_tokens

_DEFAULT_BOARD_TOKENS = get_greenhouse_tokens()

_GREENHOUSE_API_URL = (
    "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
)


def _extract_remote_type_from_metadata(metadata: list[dict[str, Any]] | None) -> str | None:
    """Infer remote type from Greenhouse metadata array."""
    if metadata is None:
        return None
    for item in metadata:
        if isinstance(item, dict) and item.get("name") == "Workplace Type":
            value = str(item.get("value", "")).strip().lower()
            if value in ("remote", "hybrid", "on-site", "onsite"):
                return "remote" if value == "remote" else (
                    "hybrid" if value == "hybrid" else "onsite"
                )
    return None


def _fetch_greenhouse_board(
    board_token: str, include_content: bool = False
) -> list[dict[str, Any]]:
    """Fetch jobs for a single Greenhouse board token."""
    url = _GREENHOUSE_API_URL.format(board_token=board_token)
    if include_content:
        url += "?content=true"

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

    jobs = data.get("jobs", [])
    if not jobs:
        return []

    results: list[dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue

        location_name = None
        location = job.get("location")
        if isinstance(location, dict):
            location_name = location.get("name", "").strip() or None

        metadata = job.get("metadata", [])
        remote_type = _extract_remote_type_from_metadata(metadata)

        raw_record: dict[str, Any] = {
            "source": "greenhouse",
            "title": _extract_string(job, "title"),
            "company": _extract_string(job, "company_name") or board_token,
            "job_url": _extract_url(job, "absolute_url"),
            "location": location_name,
            "remote_type": remote_type,
            "salary_raw": None,
            "salary_min_usd": None,
            "salary_max_usd": None,
            "posted_at": _extract_string(job, "first_published")
            or _extract_string(job, "updated_at"),
            "apply_url": None,
            "external_id": str(job.get("id", "")) or None,
            "description": _extract_string(job, "content"),
            "tags": [],
            "metadata": {
                "board_token": board_token,
                "internal_job_id": job.get("internal_job_id"),
                "requisition_id": _extract_string(job, "requisition_id"),
            },
        }
        results.append(raw_record)

    return results


def collect_greenhouse_jobs(
    board_tokens: list[str] | None = None,
    include_content: bool = False,
    delay: float = 0.1,
    max_boards: int | None = None,
    max_workers: int = 30,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from the Greenhouse Job Board API.

    Args:
        board_tokens: List of company board tokens (e.g., ["stripe", "airbnb"]).
            Defaults to a curated list if not provided.
        include_content: Whether to fetch full HTML descriptions.
        delay: Seconds to sleep between board requests (sequential mode only).
        max_boards: Maximum number of boards to query. None = all available.
        max_workers: Number of concurrent threads. >1 enables parallel fetching.

    Returns:
        List of raw job record dictionaries. Returns an empty list if
        all requests fail or no jobs are found.
    """
    tokens = board_tokens if board_tokens is not None else _DEFAULT_BOARD_TOKENS
    if max_boards is not None and max_boards > 0:
        tokens = tokens[:max_boards]

    if max_workers <= 1:
        all_results: list[dict[str, Any]] = []
        for token in tokens:
            board_jobs = _fetch_greenhouse_board(token, include_content=include_content)
            all_results.extend(board_jobs)
            if delay and len(tokens) > 1:
                time.sleep(delay)
        return all_results

    all_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_greenhouse_board, token, include_content): token
            for token in tokens
        }
        for future in as_completed(futures):
            try:
                board_jobs = future.result()
                all_results.extend(board_jobs)
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
