"""Pinpoint ATS collector.

Pinpoint (pinpointhq.com) is an applicant tracking system used by 800+
companies.  Each customer has a branded subdomain with a public,
unauthenticated JSON endpoint:

    https://{subdomain}.pinpointhq.com/postings.json

The endpoint returns a JSON object with a ``data`` array of job postings.
No API key, no CORS, no Cloudflare.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}

_BASE_URL_TEMPLATE = "https://{subdomain}.pinpointhq.com/postings.json"

# Active Pinpoint subdomains discovered via GitHub + live verification.
# Last verified: 2026-04-26 (76 active subdomains)
_PINPOINT_SUBDOMAINS: list[str] = [
    "accenture", "acrobat", "actica", "admgroup", "alcumus", "aria",
    "article", "aspireallergy", "astrolab", "auroraer", "bactobio",
    "bathspa", "betterlesson", "bighatbiosciences", "bluecross",
    "butlins", "carma", "cdlsoftware", "cfc", "cfcunderwriting",
    "chetwood-bank", "citizenm", "clearview", "coforma", "compregroup",
    "confluence", "convexin", "cottonholdings", "d1a", "davies",
    "digitalscience", "elliptic", "enosisbd", "epuki", "estalent",
    "everi", "field", "fifa-careers", "franklin-electric", "gembaadvantage",
    "grantthornton", "guernseyelectricity", "hazelcast", "hollandamericagroup",
    "icario", "impulsespace", "jed", "kempinski", "lingoda", "localiq",
    "loccitane", "lush", "made-tech", "menzies", "newfireglobal",
    "nodalexchange", "nypl", "pod-point", "portnox", "premierleague",
    "princesscruises", "sabio", "safetywing", "samsung", "scandiweb",
    "skims", "smartthings", "sunking", "tabby", "thyssenkrupp",
    "twinings", "vgroup", "whiteswandata", "workwithus", "xeneta", "ynab",
]

# Subdomains that returned empty results but may become active later.
# Kept here for documentation; not queried by default.
_PINPOINT_EMPTY: list[str] = [
    "accredible", "agencyanalytics", "amplience", "bluon", "coopereyecare",
    "db1group", "enablemedicine", "exclaimer", "fairwaygroup", "freetrade",
    "gameplaygalaxy", "hyperhippo", "knack", "merseyrail", "oncallhealth",
    "orbisoperations", "precisionneuro", "recycle", "riverisland",
    "sparelabs", "stglogistics", "superside", "swiftcomply", "tilled",
    "tripledotstudios", "turionspace", "universal", "wagepoint",
]

_MAX_WORKERS = 20
_TIMEOUT = 15


def _fetch_subdomain(subdomain: str) -> list[dict[str, Any]]:
    """Fetch job postings for a single Pinpoint subdomain."""
    url = _BASE_URL_TEMPLATE.format(subdomain=subdomain)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return []

    data = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(data, list):
        return []
    return data


def _normalize_posting(
    posting: dict[str, Any], subdomain: str
) -> dict[str, Any] | None:
    """Map a Pinpoint posting to a Job Forager raw record."""
    title = str(posting.get("title") or "").strip()
    if not title:
        return None

    posting_id = str(posting.get("id") or "").strip()
    path = str(posting.get("path") or "").strip()
    url = str(posting.get("url") or "").strip()

    # Build a permalink if url is missing
    if not url and path:
        url = f"https://{subdomain}.pinpointhq.com{path}"

    # Company name — not always present; fall back to subdomain
    company = _subdomain_to_company(subdomain)

    # Location
    location = ""
    loc_obj = posting.get("location")
    if isinstance(loc_obj, dict):
        location = str(loc_obj.get("name") or "").strip()

    # Remote type
    remote_type = None
    wt = posting.get("workplace_type")
    if wt:
        wt_lower = str(wt).lower()
        if wt_lower == "remote":
            remote_type = "remote"
        elif wt_lower == "hybrid":
            remote_type = "hybrid"
        elif wt_lower == "onsite":
            remote_type = "onsite"

    # Salary
    salary_raw = None
    salary_min_usd = None
    salary_max_usd = None
    comp = posting.get("compensation")
    if comp:
        salary_raw = str(comp).strip()
    else:
        parts: list[str] = []
        min_val = posting.get("compensation_minimum")
        max_val = posting.get("compensation_maximum")
        currency = posting.get("compensation_currency")
        frequency = posting.get("compensation_frequency")
        if min_val is not None:
            parts.append(str(min_val))
        if max_val is not None:
            parts.append(str(max_val))
        if parts:
            salary_raw = " - ".join(parts)
            if currency:
                salary_raw += f" {currency}"
            if frequency:
                salary_raw += f" / {frequency}"
        if str(currency).upper() == "USD":
            try:
                if min_val is not None:
                    salary_min_usd = int(float(min_val))
                if max_val is not None:
                    salary_max_usd = int(float(max_val))
            except (ValueError, TypeError):
                pass

    # Posted date
    posted_at = None
    for key in ("opened_at", "created_at", "updated_at"):
        val = posting.get(key)
        if val:
            posted_at = str(val).strip()
            break

    # Description
    description = posting.get("description") or ""
    if description:
        description = _strip_html(str(description))

    # Department
    dept = ""
    dept_obj = posting.get("department")
    if isinstance(dept_obj, dict):
        dept = str(dept_obj.get("name") or "").strip()

    # Employment type
    employment_type = posting.get("employment_type_text") or posting.get(
        "employment_type"
    )

    tags: list[str] = []
    if dept:
        tags.append(dept)
    if employment_type:
        tags.append(str(employment_type))

    return {
        "source": "pinpoint",
        "title": title,
        "company": company,
        "job_url": url or f"https://{subdomain}.pinpointhq.com",
        "location": location or None,
        "remote_type": remote_type,
        "salary_raw": salary_raw,
        "salary_min_usd": salary_min_usd,
        "salary_max_usd": salary_max_usd,
        "posted_at": posted_at,
        "apply_url": url or f"https://{subdomain}.pinpointhq.com",
        "external_id": posting_id or None,
        "description": description or None,
        "tags": tags,
        "metadata": {
            "subdomain": subdomain,
            "department": dept or None,
            "employment_type": str(employment_type) if employment_type else None,
            "requisition_id": posting.get("requisition_id") or None,
        },
    }


def _subdomain_to_company(subdomain: str) -> str:
    """Best-effort company name from subdomain."""
    # Known mappings
    mappings: dict[str, str] = {
        "cfc": "CFC",
        "cfcunderwriting": "CFC Underwriting",
        "nypl": "New York Public Library",
        "fifa-careers": "FIFA",
        "made-tech": "Made Tech",
        "cdlsoftware": "CDL Software",
        "hollandamericagroup": "Holland America Group",
        "franklin-electric": "Franklin Electric",
        "bighatbiosciences": "BigHat Biosciences",
        "newfireglobal": "Newfire Global",
        "premierleague": "Premier League",
        "princesscruises": "Princess Cruises",
        "smartthings": "SmartThings",
        "workwithus": "Pinpoint",
        "guernseyelectricity": "Guernsey Electricity",
    }
    if subdomain in mappings:
        return mappings[subdomain]

    # Auto-format: replace hyphens with spaces, title case
    name = subdomain.replace("-", " ").replace("_", " ")
    # Fix common abbreviations
    name = re.sub(r"\bcdl\b", "CDL", name, flags=re.IGNORECASE)
    name = re.sub(r"\bnypl\b", "NYPL", name, flags=re.IGNORECASE)
    name = re.sub(r"\bcfc\b", "CFC", name, flags=re.IGNORECASE)
    return name.title()


def _strip_html(html: str) -> str:
    """Remove HTML tags and entities from a string."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&\w+;", "", text)
    return text.strip()


def collect_pinpoint_jobs(
    search_term: str | None = None,
    location: str | None = None,
    max_results: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch jobs from all known Pinpoint subdomains.

    Results are collected concurrently and deduplicated by posting ID.
    """
    all_results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    subdomains = list(_PINPOINT_SUBDOMAINS)

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        future_to_sd = {
            executor.submit(_fetch_subdomain, sd): sd for sd in subdomains
        }
        for future in as_completed(future_to_sd):
            sd = future_to_sd[future]
            try:
                postings = future.result()
            except Exception:
                continue

            for posting in postings:
                posting_id = str(posting.get("id") or "").strip()
                if not posting_id or posting_id in seen_ids:
                    continue

                normalized = _normalize_posting(posting, sd)
                if normalized is None:
                    continue

                # Optional search-term filter (client-side)
                if search_term:
                    term_lower = search_term.lower()
                    text = " ".join(
                        [
                            normalized.get("title") or "",
                            normalized.get("description") or "",
                        ]
                    ).lower()
                    if term_lower not in text:
                        continue

                # Optional location filter (client-side)
                if location:
                    loc_lower = location.lower()
                    job_loc = (normalized.get("location") or "").lower()
                    if loc_lower not in job_loc:
                        continue

                seen_ids.add(posting_id)
                all_results.append(normalized)

                if max_results is not None and len(all_results) >= max_results:
                    return all_results

    return all_results
