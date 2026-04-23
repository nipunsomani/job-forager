"""Seed local company list data files from external GitHub repos.

Fetches the latest lists and saves them to data/ as JSON.
"""
from __future__ import annotations

import csv
import json
import os
import ssl
import urllib.request
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

_FEASHLIAA_BASE = (
    "https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data"
)
_STAPPLY_BASE = (
    "https://raw.githubusercontent.com/stapply-ai/ats-scrapers/main"
)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; jobforager/1.0)",
    "Accept": "application/json,text/csv",
}


def _http_get(url: str, timeout: float = 30.0) -> bytes:
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


def _load_json_or_defaults(url: str, defaults: list[str]) -> list[str]:
    try:
        data = _fetch_json(url)
        if isinstance(data, list):
            return data
    except Exception as exc:
        print(f"  Failed to fetch JSON from {url}: {exc}")
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
    except Exception as exc:
        print(f"  Failed to fetch CSV from {url}: {exc}")
    return defaults


def _load_workday_or_defaults(url: str, defaults: list[dict[str, str]]) -> list[dict[str, str]]:
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
    except Exception as exc:
        print(f"  Failed to fetch workday CSV from {url}: {exc}")
    return defaults


def _save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved {path} ({len(data)} entries)")


def seed_greenhouse() -> None:
    print("Seeding Greenhouse...")
    defaults = [
        "airbnb", "stripe", "figma", "anthropic", "hootsuite", "canonical",
    ]
    data = _load_json_or_defaults(
        f"{_FEASHLIAA_BASE}/greenhouse_companies.json", defaults
    )
    _save_json(os.path.join(DATA_DIR, "greenhouse_companies.json"), data)


def seed_lever() -> None:
    print("Seeding Lever...")
    defaults = ["airbnb", "netflix", "shopify", "leverdemo"]
    data = _load_json_or_defaults(
        f"{_FEASHLIAA_BASE}/lever_companies.json", defaults
    )
    _save_json(os.path.join(DATA_DIR, "lever_companies.json"), data)


def seed_ashby() -> None:
    print("Seeding Ashby...")
    defaults = ["supabase", "ramp", "figma", "linear", "vercel", "openai"]
    data = _load_json_or_defaults(
        f"{_FEASHLIAA_BASE}/ashby_companies.json", defaults
    )
    _save_json(os.path.join(DATA_DIR, "ashby_companies.json"), data)


def seed_smartrecruiters() -> None:
    print("Seeding SmartRecruiters...")
    defaults = ["adobe1", "canva", "deloitte6", "experian", "samsung1"]
    data = _load_csv_slugs_or_defaults(
        f"{_STAPPLY_BASE}/smartrecruiters/smartrecruiters_companies.csv",
        defaults,
        url_column="url",
    )
    _save_json(os.path.join(DATA_DIR, "smartrecruiters_companies.json"), data)


def seed_workday() -> None:
    print("Seeding Workday...")
    defaults = [
        {"name": "Accenture", "url": "https://accenture.wd103.myworkdayjobs.com/accenturecareers"},
        {"name": "NVIDIA", "url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"},
    ]
    # Try multiple potential paths
    urls_to_try = [
        f"{_STAPPLY_BASE}/workday/companies.csv",
        f"{_STAPPLY_BASE}/workday/workday_companies.csv",
    ]
    data: list[dict[str, str]] = []
    for url in urls_to_try:
        data = _load_workday_or_defaults(url, [])
        if data:
            print(f"  Success with {url}")
            break
    if not data:
        print("  All Workday URLs failed, using defaults")
        data = defaults
    _save_json(os.path.join(DATA_DIR, "workday_companies.json"), data)


def main() -> None:
    print(f"Data directory: {DATA_DIR}")
    seed_greenhouse()
    seed_lever()
    seed_ashby()
    seed_smartrecruiters()
    seed_workday()
    print("Done.")


if __name__ == "__main__":
    main()
