"""Company list loader for ATS platforms.

Fetches company lists from public GitHub repositories
(Feashliaa/job-board-aggregator and stapply-ai/ats-scrapers).
All fetches are live — no local caching.
"""

from __future__ import annotations

import csv
import json
import ssl
import urllib.request
from typing import Any

_FEASHLIAA_BASE = (
    "https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data"
)
_STAPPLY_BASE = (
    "https://raw.githubusercontent.com/stapply-ai/ats-scrapers/main"
)

_DEFAULT_GREENHOUSE_TOKENS = [
    "airbnb", "stripe", "figma", "anthropic", "hootsuite", "canonical",
]
_DEFAULT_LEVER_SLUGS = [
    "airbnb", "netflix", "shopify", "leverdemo",
]
_DEFAULT_ASHBY_BOARDS = [
    "supabase", "ramp", "figma", "linear", "vercel", "openai",
]

_DEFAULT_SMARTRECRUITERS_SLUGS = [
    "adobe1", "canva", "deloitte6", "experian", "samsung1",
]

_DEFAULT_WORKDAY_COMPANIES = [
    {"name": "Accenture", "url": "https://accenture.wd103.myworkdayjobs.com/accenturecareers"},
    {"name": "NVIDIA", "url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"},
]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/json,text/csv",
}


def _http_get(url: str, timeout: float = 15.0) -> bytes:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return resp.read()


def _fetch_json(url: str) -> Any:
    raw = _http_get(url)
    return json.loads(raw.decode("utf-8"))


def _fetch_csv(url: str) -> list[dict[str, str]]:
    raw = _http_get(url)
    text = raw.decode("utf-8")
    lines = text.splitlines()
    if not lines:
        return []
    reader = csv.DictReader(lines)
    return [row for row in reader if row]


def _load_json_or_defaults(url: str, defaults: list[str]) -> list[str]:
    try:
        data = _fetch_json(url)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return defaults


def _load_csv_slugs_or_defaults(
    url: str, defaults: list[str], url_column: str = "url"
) -> list[str]:
    try:
        rows = _fetch_csv(url)
        slugs: list[str] = []
        for row in rows:
            raw_url = row.get(url_column, "").strip()
            if not raw_url:
                continue
            slug = _extract_slug_from_url(raw_url)
            if slug:
                slugs.append(slug)
        if slugs:
            return slugs
    except Exception:
        pass
    return defaults


def _extract_slug_from_url(url: str) -> str | None:
    url = url.rstrip("/")
    for prefix in (
        "https://boards.greenhouse.io/",
        "https://job-boards.greenhouse.io/",
        "https://jobs.lever.co/",
        "https://jobs.ashbyhq.com/",
    ):
        if url.startswith(prefix):
            rest = url[len(prefix):]
            return rest.split("/")[0] or None
    return None


def get_greenhouse_tokens() -> list[str]:
    return _load_json_or_defaults(
        f"{_FEASHLIAA_BASE}/greenhouse_companies.json",
        _DEFAULT_GREENHOUSE_TOKENS,
    )


def get_lever_slugs() -> list[str]:
    return _load_json_or_defaults(
        f"{_FEASHLIAA_BASE}/lever_companies.json",
        _DEFAULT_LEVER_SLUGS,
    )


def get_ashby_boards() -> list[str]:
    return _load_json_or_defaults(
        f"{_FEASHLIAA_BASE}/ashby_companies.json",
        _DEFAULT_ASHBY_BOARDS,
    )


def get_smartrecruiters_slugs() -> list[str]:
    return _load_csv_slugs_or_defaults(
        f"{_STAPPLY_BASE}/smartrecruiters/smartrecruiters_companies.csv",
        _DEFAULT_SMARTRECRUITERS_SLUGS,
        url_column="url",
    )


def get_workday_companies() -> list[dict[str, str]]:
    try:
        rows = _fetch_csv(f"{_STAPPLY_BASE}/workday/companies.csv")
        companies: list[dict[str, str]] = []
        for row in rows:
            name = row.get("name", "").strip()
            url = row.get("url", "").strip()
            if name and url:
                companies.append({"name": name, "url": url})
        if companies:
            return companies
    except Exception:
        pass
    return _DEFAULT_WORKDAY_COMPANIES
