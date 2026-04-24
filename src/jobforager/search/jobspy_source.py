"""JobSpy collector for LinkedIn, Indeed, and Glassdoor.

This module wraps the ``python-jobspy`` package to scrape major job boards.
"""

from __future__ import annotations

import math
from typing import Any

from jobspy import scrape_jobs

_DEFAULT_SEARCH_TERM = ""
_DEFAULT_RESULTS_WANTED = 50
_DEFAULT_HOURS_OLD = 168  # 7 days
# JobSpy search terms with many keywords often return empty; shard long queries.
_MAX_KEYWORDS_PER_SHARD = 3


def _is_valid_number(value: Any) -> bool:
    """Return True if *value* is a real number (not None or NaN)."""
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _detect_country_indeed(location: str | None) -> str | None:
    """Return a ``country_indeed`` value for JobSpy based on *location*.

    JobSpy's Indeed scraper defaults to ``country_indeed='USA'``, which means
    a location like ``"London"`` resolves to London, Ohio rather than London,
    UK.  Passing the correct country code ensures the right Indeed domain
    (e.g. ``uk.indeed.com``) and API country context are used.
    """
    if not location:
        return None
    loc_lower = location.lower()
    if any(token in loc_lower for token in ("uk", "united kingdom", "england", "scotland", "wales", "northern ireland", "london", "manchester", "birmingham", "bristol", "leeds", "edinburgh", "glasgow", "cardiff")):
        return "UK"
    if any(token in loc_lower for token in ("usa", "united states", "us", "america", "california", "texas", "new york", "florida", "illinois", "washington", "san francisco", "seattle", "austin", "boston", "chicago", "los angeles")):
        return "USA"
    if any(token in loc_lower for token in ("canada", "ca", "toronto", "vancouver", "montreal", "ottawa", "calgary", "edmonton")):
        return "CANADA"
    if any(token in loc_lower for token in ("germany", "de", "berlin", "munich", "hamburg", "cologne", "frankfurt")):
        return "GERMANY"
    if any(token in loc_lower for token in ("france", "fr", "paris", "lyon", "marseille", "toulouse", "nice")):
        return "FRANCE"
    if any(token in loc_lower for token in ("netherlands", "nl", "amsterdam", "rotterdam", "the hague", "utrecht")):
        return "NETHERLANDS"
    if any(token in loc_lower for token in ("ireland", "ie", "dublin", "cork", "galway", "limerick")):
        return "IRELAND"
    if any(token in loc_lower for token in ("india", "in", "bangalore", "mumbai", "delhi", "hyderabad", "chennai", "pune", "kolkata")):
        return "INDIA"
    if any(token in loc_lower for token in ("australia", "au", "sydney", "melbourne", "brisbane", "perth", "adelaide")):
        return "AUSTRALIA"
    if any(token in loc_lower for token in ("singapore", "sg")):
        return "SINGAPORE"
    if any(token in loc_lower for token in ("spain", "es", "madrid", "barcelona", "valencia", "seville")):
        return "SPAIN"
    if any(token in loc_lower for token in ("italy", "it", "rome", "milan", "naples", "turin", "florence")):
        return "ITALY"
    if any(token in loc_lower for token in ("switzerland", "ch", "zurich", "geneva", "basel", "bern")):
        return "SWITZERLAND"
    if any(token in loc_lower for token in ("sweden", "se", "stockholm", "gothenburg", "malmo")):
        return "SWEDEN"
    if any(token in loc_lower for token in ("poland", "pl", "warsaw", "krakow", "wroclaw", "gdansk")):
        return "POLAND"
    if any(token in loc_lower for token in ("portugal", "pt", "lisbon", "porto", "braga")):
        return "PORTUGAL"
    if any(token in loc_lower for token in ("brazil", "br", "sao paulo", "rio de janeiro", "brasilia", "salvador")):
        return "BRAZIL"
    if any(token in loc_lower for token in ("mexico", "mx", "mexico city", "guadalajara", "monterrey")):
        return "MEXICO"
    if any(token in loc_lower for token in ("argentina", "ar", "buenos aires", "cordoba", "rosario")):
        return "ARGENTINA"
    if any(token in loc_lower for token in ("south africa", "za", "johannesburg", "cape town", "durban")):
        return "SOUTH_AFRICA"
    if any(token in loc_lower for token in ("uae", "united arab emirates", "dubai", "abu dhabi", "sharjah")):
        return "UNITED_ARAB_EMIRATES"
    if any(token in loc_lower for token in ("japan", "jp", "tokyo", "osaka", "kyoto", "yokohama")):
        return "JAPAN"
    if any(token in loc_lower for token in ("south korea", "kr", "seoul", "busan", "incheon")):
        return "SOUTH_KOREA"
    if any(token in loc_lower for token in ("philippines", "ph", "manila", "cebu", "davao")):
        return "PHILIPPINES"
    if any(token in loc_lower for token in ("indonesia", "id", "jakarta", "surabaya", "bandung")):
        return "INDONESIA"
    if any(token in loc_lower for token in ("malaysia", "my", "kuala lumpur", "penang", "johor bahru")):
        return "MALAYSIA"
    if any(token in loc_lower for token in ("thailand", "th", "bangkok", "chiang mai", "phuket")):
        return "THAILAND"
    if any(token in loc_lower for token in ("vietnam", "vn", "ho chi minh", "hanoi", "da nang")):
        return "VIETNAM"
    if any(token in loc_lower for token in ("nigeria", "ng", "lagos", "abuja", "ibadan")):
        return "NIGERIA"
    if any(token in loc_lower for token in ("kenya", "ke", "nairobi", "mombasa")):
        return "KENYA"
    if any(token in loc_lower for token in ("egypt", "eg", "cairo", "alexandria", "giza")):
        return "EGYPT"
    if any(token in loc_lower for token in ("turkey", "tr", "istanbul", "ankara", "izmir")):
        return "TURKEY"
    if any(token in loc_lower for token in ("israel", "il", "tel aviv", "jerusalem", "haifa")):
        return "ISRAEL"
    if any(token in loc_lower for token in ("new zealand", "nz", "auckland", "wellington", "christchurch")):
        return "NEW_ZEALAND"
    if any(token in loc_lower for token in ("denmark", "dk", "copenhagen", "aarhus", "odense")):
        return "DENMARK"
    if any(token in loc_lower for token in ("norway", "no", "oslo", "bergen", "trondheim")):
        return "NORWAY"
    if any(token in loc_lower for token in ("finland", "fi", "helsinki", "espoo", "tampere")):
        return "FINLAND"
    if any(token in loc_lower for token in ("belgium", "be", "brussels", "antwerp", "ghent")):
        return "BELGIUM"
    if any(token in loc_lower for token in ("austria", "at", "vienna", "salzburg", "graz", "linz")):
        return "AUSTRIA"
    if any(token in loc_lower for token in ("czech republic", "cz", "prague", "brno", "ostrava")):
        return "CZECH_REPUBLIC"
    if any(token in loc_lower for token in ("hungary", "hu", "budapest", "debrecen", "szeged")):
        return "HUNGARY"
    if any(token in loc_lower for token in ("romania", "ro", "bucharest", "cluj", "timisoara")):
        return "ROMANIA"
    if any(token in loc_lower for token in ("bulgaria", "bg", "sofia", "plovdiv", "varna")):
        return "BULGARIA"
    if any(token in loc_lower for token in ("croatia", "hr", "zagreb", "split", "rijeka")):
        return "CROATIA"
    if any(token in loc_lower for token in ("slovenia", "si", "ljubljana", "maribor")):
        return "SLOVENIA"
    if any(token in loc_lower for token in ("slovakia", "sk", "bratislava", "kosice")):
        return "SLOVAKIA"
    if any(token in loc_lower for token in ("estonia", "ee", "tallinn", "tartu")):
        return "ESTONIA"
    if any(token in loc_lower for token in ("latvia", "lv", "riga", "daugavpils")):
        return "LATVIA"
    if any(token in loc_lower for token in ("lithuania", "lt", "vilnius", "kaunas")):
        return "LITHUANIA"
    if any(token in loc_lower for token in ("luxembourg", "lu", "luxembourg city")):
        return "LUXEMBOURG"
    if any(token in loc_lower for token in ("cyprus", "cy", "nicosia", "limassol")):
        return "CYPRUS"
    if any(token in loc_lower for token in ("malta", "mt", "valletta", "sliema")):
        return "MALTA"
    if any(token in loc_lower for token in ("iceland", "is", "reykjavik")):
        return "ICELAND"
    return None


def _map_jobspy_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Map a single JobSpy DataFrame row to a Job Forager raw record."""
    title = str(row.get("title") or "").strip()
    company = str(row.get("company") or "").strip()
    job_url = str(row.get("job_url") or "").strip()

    if not title or not company or not job_url:
        return None

    remote_type = None
    if row.get("is_remote") is True:
        remote_type = "remote"
    elif row.get("is_remote") is False:
        remote_type = "onsite"

    location = str(row.get("location") or "").strip() or None

    # Salary handling — guard against NaN from pandas
    min_amount = row.get("min_amount")
    max_amount = row.get("max_amount")
    currency = str(row.get("currency") or "").strip().upper()
    interval = str(row.get("interval") or "").strip().lower()

    salary_raw = None
    if _is_valid_number(min_amount) or _is_valid_number(max_amount):
        parts: list[str] = []
        if _is_valid_number(min_amount):
            parts.append(str(min_amount))
        if _is_valid_number(max_amount):
            parts.append(str(max_amount))
        if interval:
            parts.append(interval)
        if currency:
            parts.append(currency)
        salary_raw = " - ".join(parts)

    salary_min_usd = None
    salary_max_usd = None
    if currency == "USD" and _is_valid_number(min_amount):
        salary_min_usd = int(float(min_amount))
    if currency == "USD" and _is_valid_number(max_amount):
        salary_max_usd = int(float(max_amount))

    posted_at = str(row.get("date_posted") or "").strip() or None
    description = str(row.get("description") or "").strip() or None

    job_type = str(row.get("job_type") or "").strip()
    tags = [job_type] if job_type else []

    site = str(row.get("site") or "jobspy").lower()

    return {
        "source": site,
        "title": title,
        "company": company,
        "job_url": job_url,
        "location": location,
        "remote_type": remote_type,
        "salary_raw": salary_raw,
        "salary_min_usd": salary_min_usd,
        "salary_max_usd": salary_max_usd,
        "posted_at": posted_at,
        "apply_url": job_url,
        "external_id": str(row.get("id") or "").strip() or None,
        "description": description,
        "tags": tags,
        "metadata": {
            "jobspy_interval": interval or None,
            "jobspy_currency": currency or None,
            "jobspy_salary_source": row.get("salary_source") or None,
        },
    }


def _scrape_once(
    site_name: str,
    search_term: str | None,
    location: str | None,
    results_wanted: int,
    hours_old: int | None,
) -> list[dict[str, Any]]:
    """Single scrape_jobs call with error handling."""
    try:
        # Glassdoor can't parse free-text locations; skip it to avoid 400 errors
        loc = None if site_name.lower() == "glassdoor" else location
        extra_kwargs: dict[str, Any] = {}
        if site_name.lower() == "indeed":
            country = _detect_country_indeed(location)
            if country:
                extra_kwargs["country_indeed"] = country
        jobs_df = scrape_jobs(
            site_name=[site_name],
            search_term=search_term,
            location=loc,
            results_wanted=results_wanted,
            hours_old=hours_old,
            **extra_kwargs,
        )
    except Exception:
        return []

    if jobs_df is None or getattr(jobs_df, "empty", True):
        return []

    results: list[dict[str, Any]] = []
    for row in jobs_df.to_dict("records"):
        mapped = _map_jobspy_row(row)
        if mapped is not None:
            results.append(mapped)
    return results


def _shard_search_term(search_term: str | None) -> list[str]:
    """Split a long search term into keyword shards."""
    if not search_term:
        return [""]

    # Split on commas or spaces
    keywords = [
        k.strip() for k in search_term.replace(",", " ").split() if k.strip()
    ]
    if len(keywords) <= _MAX_KEYWORDS_PER_SHARD:
        return [search_term]

    shards: list[str] = []
    for i in range(0, len(keywords), _MAX_KEYWORDS_PER_SHARD):
        shard = keywords[i : i + _MAX_KEYWORDS_PER_SHARD]
        shards.append(" ".join(shard))
    return shards


def _collect_jobspy_for_site(
    site_name: str,
    search_term: str | None = None,
    location: str | None = None,
    results_wanted: int = _DEFAULT_RESULTS_WANTED,
    hours_old: int | None = _DEFAULT_HOURS_OLD,
) -> list[dict[str, Any]]:
    """Fetch jobs from a single JobSpy-supported site.

    Long search terms are automatically sharded into smaller queries so that
    every keyword is searched without overwhelming the target site.
    """
    shards = _shard_search_term(search_term)

    # If there's only one shard, run it directly
    if len(shards) == 1:
        return _scrape_once(
            site_name, shards[0], location, results_wanted, hours_old
        )

    # Multiple shards — run each and deduplicate by job_url
    all_results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for shard_term in shards:
        results = _scrape_once(
            site_name, shard_term, location, results_wanted, hours_old
        )
        for job in results:
            url = job.get("job_url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(job)

    return all_results


def collect_linkedin_jobs(
    search_term: str | None = None,
    location: str | None = None,
    results_wanted: int = _DEFAULT_RESULTS_WANTED,
    hours_old: int | None = _DEFAULT_HOURS_OLD,
) -> list[dict[str, Any]]:
    """Fetch jobs from LinkedIn via JobSpy."""
    return _collect_jobspy_for_site(
        "linkedin",
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )


def collect_indeed_jobs(
    search_term: str | None = None,
    location: str | None = None,
    results_wanted: int = _DEFAULT_RESULTS_WANTED,
    hours_old: int | None = _DEFAULT_HOURS_OLD,
) -> list[dict[str, Any]]:
    """Fetch jobs from Indeed via JobSpy."""
    return _collect_jobspy_for_site(
        "indeed",
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )


def collect_glassdoor_jobs(
    search_term: str | None = None,
    location: str | None = None,
    results_wanted: int = _DEFAULT_RESULTS_WANTED,
    hours_old: int | None = _DEFAULT_HOURS_OLD,
) -> list[dict[str, Any]]:
    """Fetch jobs from Glassdoor via JobSpy."""
    return _collect_jobspy_for_site(
        "glassdoor",
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )
