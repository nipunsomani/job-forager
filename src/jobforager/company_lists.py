"""Company list loader for ATS platforms.

Loads company lists from local JSON files and fetches fresh lists from
public GitHub repositories (Feashliaa/job-board-aggregator and
stapply-ai/ats-scrapers). Merges external data into local files so the
database grows over time.
"""

from __future__ import annotations

import csv
import json
import ssl
import urllib.request
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

_FEASHLIAA_BASE = (
    "https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data"
)
_STAPPLY_BASE = (
    "https://raw.githubusercontent.com/stapply-ai/ats-scrapers/main"
)

_DEFAULT_GREENHOUSE_TOKENS = [
    "airbnb", "stripe", "figma", "anthropic", "hootsuite", "canonical",
    "wehrtyou", "monzo", "tide",
]
_DEFAULT_LEVER_SLUGS = [
    "airbnb", "netflix", "shopify", "leverdemo",
    "zopa",
]
_DEFAULT_ASHBY_BOARDS = [
    "supabase", "ramp", "figma", "linear", "vercel", "openai",
    "clearbank",
]

_DEFAULT_SMARTRECRUITERS_SLUGS = [
    "adobe1", "canva", "deloitte6", "experian", "samsung1",
    "wise",
]

_DEFAULT_WORKDAY_COMPANIES = [
    {"name": "Accenture", "url": "https://accenture.wd103.myworkdayjobs.com/accenturecareers"},
    {"name": "NVIDIA", "url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"},
    {"name": "Morgan Stanley", "url": "https://ms.wd5.myworkdayjobs.com/External"},
    {"name": "Deutsche Bank", "url": "https://db.wd3.myworkdayjobs.com/DBWebsite"},
    {"name": "Brevan Howard", "url": "https://wd3.myworkdaysite.com/recruiting/brevanhoward/BH_ExternalCareers"},
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


def _load_local_json(path: Path) -> list[str] | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data if isinstance(x, str)]
    except Exception:
        pass
    return None


def _save_local_json(path: Path, data: list[str]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _merge_string_lists(local: list[str], fetched: list[str]) -> list[str]:
    return sorted(set(local + fetched))


def _load_and_merge_string_list(
    local_path: Path,
    fetch_url: str,
    defaults: list[str],
) -> list[str]:
    local_data: list[str] = []
    loaded = _load_local_json(local_path)
    if loaded is not None:
        local_data = loaded

    try:
        fetched = _fetch_json(fetch_url)
        if isinstance(fetched, list):
            fetched_data = [str(x) for x in fetched if isinstance(x, str)]
            merged = _merge_string_lists(local_data or defaults, fetched_data)
            _save_local_json(local_path, merged)
            return merged
    except Exception:
        pass

    if local_data:
        return local_data
    return defaults


def _extract_slug_from_url(url: str) -> str | None:
    url = url.rstrip("/")
    for prefix in (
        "https://boards.greenhouse.io/",
        "https://job-boards.greenhouse.io/",
        "https://jobs.lever.co/",
        "https://jobs.ashbyhq.com/",
        "https://jobs.smartrecruiters.com/",
    ):
        if url.startswith(prefix):
            rest = url[len(prefix):]
            return rest.split("/")[0] or None
    return None


def _load_csv_slugs(url: str, url_column: str = "url") -> list[str] | None:
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
    return None


def _load_and_merge_csv_slug_list(
    local_path: Path,
    fetch_url: str,
    defaults: list[str],
    url_column: str = "url",
) -> list[str]:
    local_data: list[str] = []
    loaded = _load_local_json(local_path)
    if loaded is not None:
        local_data = loaded

    fetched = _load_csv_slugs(fetch_url, url_column)
    if fetched is not None:
        merged = _merge_string_lists(local_data or defaults, fetched)
        _save_local_json(local_path, merged)
        return merged

    if local_data:
        return local_data
    return defaults


def get_greenhouse_tokens() -> list[str]:
    return _load_and_merge_string_list(
        _DATA_DIR / "greenhouse_companies.json",
        f"{_FEASHLIAA_BASE}/greenhouse_companies.json",
        _DEFAULT_GREENHOUSE_TOKENS,
    )


def get_lever_slugs() -> list[str]:
    return _load_and_merge_string_list(
        _DATA_DIR / "lever_companies.json",
        f"{_FEASHLIAA_BASE}/lever_companies.json",
        _DEFAULT_LEVER_SLUGS,
    )


def get_ashby_boards() -> list[str]:
    return _load_and_merge_string_list(
        _DATA_DIR / "ashby_companies.json",
        f"{_FEASHLIAA_BASE}/ashby_companies.json",
        _DEFAULT_ASHBY_BOARDS,
    )


def get_smartrecruiters_slugs() -> list[str]:
    return _load_and_merge_csv_slug_list(
        _DATA_DIR / "smartrecruiters_companies.json",
        f"{_STAPPLY_BASE}/smartrecruiters/smartrecruiters_companies.csv",
        _DEFAULT_SMARTRECRUITERS_SLUGS,
        url_column="url",
    )


def _load_local_workday(path: Path) -> list[dict[str, str]] | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [
                {"name": str(row.get("name", "")), "url": str(row.get("url", ""))}
                for row in data
                if isinstance(row, dict) and row.get("url")
            ]
    except Exception:
        pass
    return None


def _save_local_workday(path: Path, data: list[dict[str, str]]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _merge_workday_lists(
    local: list[dict[str, str]],
    fetched: list[dict[str, str]],
) -> list[dict[str, str]]:
    seen = {row["url"] for row in local}
    merged = list(local)
    for row in fetched:
        if row["url"] not in seen:
            merged.append(row)
            seen.add(row["url"])
    return merged


def _load_workday_csv(url: str) -> list[dict[str, str]] | None:
    try:
        rows = _fetch_csv(url)
        companies: list[dict[str, str]] = []
        for row in rows:
            name = row.get("name", "").strip()
            url_val = row.get("url", "").strip()
            if name and url_val:
                companies.append({"name": name, "url": url_val})
        if companies:
            return companies
    except Exception:
        pass
    return None


def get_workday_companies() -> list[dict[str, str]]:
    local_path = _DATA_DIR / "workday_companies.json"
    local_data = _load_local_workday(local_path)

    defaults = _DEFAULT_WORKDAY_COMPANIES
    base = _merge_workday_lists(defaults, local_data or [])

    fetched = None
    for url_suffix in (
        f"{_STAPPLY_BASE}/workday/companies.csv",
        f"{_STAPPLY_BASE}/workday/workday_companies.csv",
    ):
        fetched = _load_workday_csv(url_suffix)
        if fetched is not None:
            break

    if fetched is not None:
        merged = _merge_workday_lists(base, fetched)
        _save_local_workday(local_path, merged)
        return merged

    return base
