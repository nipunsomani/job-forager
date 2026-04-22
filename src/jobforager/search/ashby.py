"""Ashby public job postings API collector for job listings."""

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

from jobforager.company_lists import get_ashby_boards

_DEFAULT_BOARD_NAMES = get_ashby_boards()

_ASHBY_API_URL = (
    "https://api.ashbyhq.com/posting-api/job-board/{board_name}"
    "?includeCompensation={include_compensation}"
)

_ASHBY_WORKPLACE_MAP = {
    "remote": "remote",
    "onsite": "onsite",
    "on-site": "onsite",
    "hybrid": "hybrid",
}


def _extract_salary_info(
    compensation: dict[str, Any] | None,
) -> tuple[str | None, int | None, int | None]:
    """Extract salary summary and min/max USD from Ashby compensation object."""
    if not isinstance(compensation, dict):
        return None, None, None

    salary_raw = compensation.get("compensationTierSummary")
    summary = salary_raw if isinstance(salary_raw, str) else None

    salary_min = None
    salary_max = None
    components = compensation.get("summaryComponents", [])
    if isinstance(components, list):
        for component in components:
            if isinstance(component, dict) and component.get("compensationType") == "Salary":
                min_val = component.get("minValue")
                max_val = component.get("maxValue")
                if isinstance(min_val, (int, float)):
                    salary_min = int(min_val)
                if isinstance(max_val, (int, float)):
                    salary_max = int(max_val)
                break

    return summary, salary_min, salary_max


def _fetch_ashby_board(
    board_name: str, include_compensation: bool = False
) -> list[dict[str, Any]]:
    """Fetch jobs for a single Ashby board name."""
    url = _ASHBY_API_URL.format(
        board_name=board_name,
        include_compensation="true" if include_compensation else "false",
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
        return []

    jobs = data.get("jobs", [])
    if not jobs:
        return []

    results: list[dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue

        workplace_raw = str(job.get("workplaceType", "")).strip().lower()
        remote_type = _ASHBY_WORKPLACE_MAP.get(workplace_raw)

        salary_raw, salary_min, salary_max = _extract_salary_info(
            job.get("compensation")
        )

        tags: list[str] = []
        department = _extract_string(job, "department")
        team = _extract_string(job, "team")
        if department:
            tags.append(department)
        if team:
            tags.append(team)

        raw_record: dict[str, Any] = {
            "source": "ashby",
            "title": _extract_string(job, "title"),
            "company": board_name,
            "job_url": _extract_url(job, "jobUrl"),
            "location": _extract_string(job, "location"),
            "remote_type": remote_type,
            "salary_raw": salary_raw,
            "salary_min_usd": salary_min,
            "salary_max_usd": salary_max,
            "posted_at": _extract_string(job, "publishedAt"),
            "apply_url": _extract_url(job, "applyUrl"),
            "external_id": None,
            "description": _extract_string(job, "descriptionPlain")
            or _extract_string(job, "descriptionHtml"),
            "tags": tags,
            "metadata": {
                "board_name": board_name,
                "employment_type": job.get("employmentType"),
                "is_remote": job.get("isRemote"),
            },
        }
        results.append(raw_record)

    return results


def collect_ashby_jobs(
    board_names: list[str] | None = None,
    include_compensation: bool = False,
    delay: float = 0.1,
    max_boards: int | None = None,
    max_workers: int = 30,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from the Ashby public job postings API.

    Args:
        board_names: List of Ashby board names (e.g., ["supabase", "figma"]).
            Defaults to a curated list if not provided.
        include_compensation: Whether to include compensation data.
        delay: Seconds to sleep between board requests (sequential mode only).
        max_boards: Maximum number of boards to query. None = all available.
        max_workers: Number of concurrent threads. >1 enables parallel fetching.

    Returns:
        List of raw job record dictionaries. Returns an empty list if
        all requests fail or no jobs are found.
    """
    names = board_names if board_names is not None else _DEFAULT_BOARD_NAMES
    if max_boards is not None and max_boards > 0:
        names = names[:max_boards]

    if max_workers <= 1:
        all_results: list[dict[str, Any]] = []
        for name in names:
            board_jobs = _fetch_ashby_board(name, include_compensation=include_compensation)
            all_results.extend(board_jobs)
            if delay and len(names) > 1:
                time.sleep(delay)
        return all_results

    all_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_ashby_board, name, include_compensation): name
            for name in names
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
