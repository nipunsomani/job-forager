"""Hiring.cafe API collector for job listings.

Falls back through three transport layers:
1. Standard urllib (fastest, works if no bot protection)
2. curl_cffi with TLS fingerprint spoofing (bypasses some WAFs)
3. Playwright browser automation (bypasses Cloudflare JS challenge
   when the user's IP reputation allows it)
"""

import json
import ssl
import urllib.request
from typing import Any

try:
    from curl_cffi import requests as curl_requests

    _CURL_CFFI_AVAILABLE = True
except Exception:
    _CURL_CFFI_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright

    _PLAYWRIGHT_AVAILABLE = True
except Exception:
    _PLAYWRIGHT_AVAILABLE = False

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Referer": "https://hiring.cafe/",
    "Origin": "https://hiring.cafe",
}

_BASE_URL = "https://hiring.cafe"
_COUNT_URL = f"{_BASE_URL}/api/search-jobs/get-total-count"
_JOBS_URL = f"{_BASE_URL}/api/search-jobs"
_PAGE_SIZE = 1000


def _build_search_state(
    search_query: str = "",
    location: str = "",
    remote_only: bool = False,
) -> dict[str, Any]:
    """Build minimal searchState payload."""
    state: dict[str, Any] = {
        "searchQuery": search_query,
        "locations": [],
        "workplaceTypes": ["Remote", "Hybrid", "Onsite"],
        "defaultToUserLocation": False,
        "userLocation": None,
        "commitmentTypes": [
            "Full Time", "Part Time", "Contract", "Internship",
            "Temporary", "Seasonal", "Volunteer",
        ],
        "seniorityLevel": [
            "No Prior Experience Required", "Entry Level", "Mid Level",
        ],
        "roleYoeRange": [0, 20],
        "excludeIfRoleYoeIsNotSpecified": False,
        "managementYoeRange": [0, 20],
        "excludeIfManagementYoeIsNotSpecified": False,
        "securityClearances": [
            "None", "Confidential", "Secret", "Top Secret",
            "Top Secret/SCI", "Public Trust", "Interim Clearances", "Other",
        ],
        "dateFetchedPastNDays": 61,
        "sortBy": "default",
    }

    if location:
        state["locations"] = [
            {
                "formatted_address": location,
                "types": ["country"],
                "geometry": {"location": {"lat": "0", "lon": "0"}},
                "options": {
                    "flexible_regions": ["anywhere_in_continent", "anywhere_in_world"]
                },
            }
        ]

    if remote_only:
        state["workplaceTypes"] = ["Remote"]

    return state


def _fetch_with_curl_cffi(url: str, payload: bytes) -> dict[str, Any] | None:
    if not _CURL_CFFI_AVAILABLE:
        return None
    try:
        resp = curl_requests.post(
            url,
            data=payload,
            headers=_DEFAULT_HEADERS,
            impersonate="chrome131",
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def _fetch_with_playwright(url: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not _PLAYWRIGHT_AVAILABLE:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            page = context.new_page()
            page.goto("https://hiring.cafe", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            if "Just a moment" in page.title():
                page.wait_for_timeout(10000)

            result = page.evaluate(
                """async (endpoint, body) => {
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(body)
                    });
                    return {
                        ok: response.ok,
                        status: response.status,
                        data: await response.json()
                    };
                }""",
                [url, payload],
            )
            browser.close()
            if result.get("ok"):
                return result.get("data")
    except Exception:
        pass
    return None


def _fetch_total_count(search_state: dict[str, Any]) -> int:
    payload_dict = {"searchState": search_state}
    payload = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request(
        _COUNT_URL, data=payload, headers=_DEFAULT_HEADERS, method="POST"
    )

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("total", 0)
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            data = _fetch_with_curl_cffi(_COUNT_URL, payload)
            if data is not None:
                return data.get("total", 0)
            data = _fetch_with_playwright(_COUNT_URL, payload_dict)
            if data is not None:
                return data.get("total", 0)
        return 0
    except Exception:
        return 0


def _fetch_jobs_page(
    search_state: dict[str, Any], page: int
) -> list[dict[str, Any]]:
    payload_dict = {"size": _PAGE_SIZE, "page": page, "searchState": search_state}
    payload = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request(
        _JOBS_URL, data=payload, headers=_DEFAULT_HEADERS, method="POST"
    )

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("results", [])
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            data = _fetch_with_curl_cffi(_JOBS_URL, payload)
            if data is not None:
                return data.get("results", [])
            data = _fetch_with_playwright(_JOBS_URL, payload_dict)
            if data is not None:
                return data.get("results", [])
        return []
    except Exception:
        return []


def _strip_html(html: str) -> str:
    import re

    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&\w+;", "", text)
    return text.strip()


def _normalize_job(job: dict[str, Any]) -> dict[str, Any] | None:
    job_info = job.get("job_information") or {}
    title = job_info.get("title", "").strip()
    company = job.get("source", "").strip()
    url = job.get("apply_url", "").strip()

    if not title or not company or not url:
        return None

    description = job_info.get("description", "")
    if description:
        description = _strip_html(description)

    return {
        "source": "hiringcafe",
        "title": title,
        "company": company,
        "job_url": url,
        "location": None,
        "remote_type": None,
        "salary_raw": None,
        "salary_min_usd": None,
        "salary_max_usd": None,
        "posted_at": None,
        "apply_url": url,
        "external_id": job.get("id"),
        "description": description or None,
        "tags": [],
        "metadata": {
            "board_token": job.get("board_token"),
            "source_and_board_token": job.get("source_and_board_token"),
            "viewed_count": len(job_info.get("viewedByUsers", [])),
            "applied_count": len(job_info.get("appliedFromUsers", [])),
            "saved_count": len(job_info.get("savedFromUsers", [])),
            "hidden_count": len(job_info.get("hiddenFromUsers", [])),
        },
    }


def collect_hiringcafe_jobs(
    search_query: str = "",
    location: str = "",
    remote_only: bool = False,
    max_results: int | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from hiring.cafe API.

    Args:
        search_query: Search term for job titles/descriptions.
        location: Location filter (country or city name).
        remote_only: Only return remote jobs.
        max_results: Maximum jobs to fetch. None = fetch all.

    Returns:
        List of raw job record dictionaries.
    """
    search_state = _build_search_state(search_query, location, remote_only)
    total = _fetch_total_count(search_state)

    if not total:
        return []

    if max_results is not None:
        total = min(total, max_results)

    all_jobs: list[dict[str, Any]] = []
    page = 0

    while len(all_jobs) < total:
        results = _fetch_jobs_page(search_state, page)
        if not results:
            break

        for job in results:
            normalized = _normalize_job(job)
            if normalized:
                all_jobs.append(normalized)

            if max_results is not None and len(all_jobs) >= max_results:
                break

        if len(results) < _PAGE_SIZE:
            break

        page += 1

    return all_jobs
