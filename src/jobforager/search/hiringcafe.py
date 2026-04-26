"""Hiring.cafe collector using Next.js data API.

Fetches jobs via HiringCafe's Next.js SSR data endpoint, which returns
structured JSON without requiring browser automation or TLS spoofing.

Build ID auto-discovery
-----------------------
Next.js embeds a per-deploy ``buildId`` in the ``/_next/data/{buildId}/``
URL path.  When HiringCafe redeploys the old ID starts returning **404**.
The 404 response body *contains the current buildId*, so we can extract it
on-the-fly and retry (see ``_get_build_id`` and ``_fetch_page``).

Dynamic location resolution
---------------------------
Instead of a hard-coded country whitelist we call
``/api/searchLocation?query=…`` at runtime.  The endpoint is unrestricted
(no Cloudflare, no auth) and returns Algolia/Google-Places style location
objects.

Union (OR) logic for multiple locations
---------------------------------------
When ``--location "UK,London,remote"`` is passed we treat each token as an
*independent* criterion and **union** the results:

* Geo-locations are searched separately and merged (deduplicated by job ID).
* City-level ``locality`` hits (e.g. London, San Francisco) are searched at
  their parent **country** level and then post-filtered for the city name.
* Workplace-type tokens (``remote``, ``hybrid``, ``onsite``) are applied as
  a **post-filter** on the merged geo results.  If *only* a workplace type
  is given the search is global.
"""

from __future__ import annotations

import json
import math
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Referer": "https://hiring.cafe/",
    "x-nextjs-data": "1",
}

_BASE_URL = "https://hiring.cafe"

# Module-level mutable cache so the buildId is discovered at most once
# per process life-time.
_build_id_cache: str | None = None

# Pre-API-call normalisation for abbreviations that mis-resolve
# (verified against the live ``/api/searchLocation`` endpoint).
_LOCATION_SYNONYMS: dict[str, str] = {
    "uk": "U.K.",
    "gb": "U.K.",
    "great britain": "United Kingdom",
    "usa": "United States",
    "us": "United States",
    "america": "United States",
    "ca": "Canada",
    "de": "Germany",
    "wales": "United Kingdom",
    "scotland": "United Kingdom",
    "england": "United Kingdom",
    "ny": "New York",
    "nyc": "New York",
    "sf": "San Francisco",
    "la": "Los Angeles",
}

# Tokens that are workplace-type filters, not geo locations.
_WORKPLACE_TYPES = {"remote", "hybrid", "onsite", "anywhere", "worldwide"}

# Maximum results per search query (the API returns ~100-130 per query)
_MAX_RESULTS_PER_QUERY = 120
# Shard long search terms like JobSpy (the API treats space-separated
# keywords as an AND query; very long strings may silently truncate)
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


def _strip_html(html: str) -> str:
    """Remove HTML tags and entities from a string."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&\w+;", "", text)
    return text.strip()


def _shard_search_term(search_term: str | None) -> list[str]:
    """Split a long search term into keyword shards."""
    if not search_term:
        return [""]

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


def _discover_build_id_from_404(body: bytes) -> str | None:
    """Extract the current buildId from a Next.js 404 response body."""
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        return None
    m = re.search(r'"buildId":"([^"]+)"', text)
    if m:
        return m.group(1)
    return None


def _get_build_id() -> str | None:
    """Return the current HiringCafe Next.js buildId.

    Uses a module-level cache so we only discover it once per run.
    If the cached ID is stale, the first 404 response from ``_fetch_page``
    will trigger re-discovery and update the cache.
    """
    global _build_id_cache
    if _build_id_cache is not None:
        return _build_id_cache

    # Seed with a known historical ID so the first request has a chance
    # of working.  If it fails we auto-discover from the 404 body.
    candidates = ["rNM3CB7RcWaQ3BT2siD_a", "BSfMOoCHeSpj01n-FYLak"]

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for bid in candidates:
        url = f"{_BASE_URL}/_next/data/{bid}/index.json?searchState=%7B%7D"
        req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                _build_id_cache = bid
                return bid
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                new_bid = _discover_build_id_from_404(exc.read())
                if new_bid and new_bid != bid:
                    # Verify the discovered ID actually works
                    url2 = (
                        f"{_BASE_URL}/_next/data/{new_bid}/"
                        f"index.json?searchState=%7B%7D"
                    )
                    req2 = urllib.request.Request(url2, headers=_DEFAULT_HEADERS)
                    try:
                        with urllib.request.urlopen(
                            req2, context=ctx, timeout=15
                        ) as resp:
                            _build_id_cache = new_bid
                            return new_bid
                    except Exception:
                        pass
        except Exception:
            pass

    return None


def _resolve_location(query: str | None) -> dict[str, Any] | None:
    """Call ``/api/searchLocation`` and return the first result's wrapper.

    The wrapper (``label`` + ``value`` + ``placeDetail``) is what the
    Next.js data API expects in ``searchState.locations``.  Returning
    ``placeDetail`` alone causes city-level ``locality`` locations to
    return 0 hits.
    """
    if not query:
        return None
    url = f"{_BASE_URL}/api/searchLocation?query={urllib.parse.quote(query)}"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": _DEFAULT_HEADERS["User-Agent"],
                "Referer": "https://hiring.cafe/",
                "Accept": "*/*",
            },
        )
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            results = json.loads(resp.read().decode("utf-8"))
            if results and isinstance(results, list) and len(results) > 0:
                return results[0]
    except Exception:
        pass

    return None


def _parse_location_input(location: str | None) -> tuple[list[str], list[str]]:
    """Split a raw ``--location`` string into geo queries and workplace types.

    Returns ``(geo_queries, workplace_types)``.

    Example:
        ``"UK, London, remote"`` → ``(["U.K.", "London"], ["remote"])``
    """
    if not location:
        return [], []

    geo_queries: list[str] = []
    workplace_types: list[str] = []

    for token in location.split(","):
        token = token.strip().lower()
        if not token:
            continue
        if token in _WORKPLACE_TYPES:
            workplace_types.append(token)
            continue
        # Apply synonym remapping
        geo_queries.append(_LOCATION_SYNONYMS.get(token, token))

    return geo_queries, workplace_types


def _extract_country_from_wrapper(
    wrapper: dict[str, Any],
) -> dict[str, Any] | None:
    """Return the country-level wrapper for a city-level location.

    The API only filters at ``country`` or ``administrative_area_level_1``
    level; ``locality`` (city) returns 0 hits.  When we get a city we
    extract the country from ``address_components`` and resolve it.
    """
    pd = wrapper.get("placeDetail") or {}
    types = pd.get("types") or []
    if "country" in types:
        return wrapper  # Already country level

    # Find the country component
    for comp in pd.get("address_components", []):
        if "country" in (comp.get("types") or []):
            country_name = comp.get("long_name")
            if country_name:
                return _resolve_location(country_name)

    # Fallback: use formatted_address if it contains a country
    fmt = pd.get("formatted_address", "")
    parts = [p.strip() for p in fmt.split(",")]
    if len(parts) >= 2:
        return _resolve_location(parts[-1])

    return wrapper


def _fetch_page(
    search_state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Fetch one page of jobs from the Next.js data API.

    Automatically handles stale buildIds by extracting the current one
    from a 404 response body and retrying once.
    """
    global _build_id_cache

    build_id = _get_build_id()
    if not build_id:
        return []

    encoded = urllib.parse.quote(json.dumps(search_state))
    url = f"{_BASE_URL}/_next/data/{build_id}/index.json?searchState={encoded}"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            new_bid = _discover_build_id_from_404(exc.read())
            if new_bid and new_bid != build_id:
                _build_id_cache = new_bid
                url = (
                    f"{_BASE_URL}/_next/data/{new_bid}/"
                    f"index.json?searchState={encoded}"
                )
                try:
                    req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
                    with urllib.request.urlopen(
                        req, context=ctx, timeout=30
                    ) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                except Exception:
                    return []
            else:
                return []
        else:
            return []
    except Exception:
        return []

    # The response shape is {"pageProps": {...}, "__N_SSP": 1}
    page_props = data.get("pageProps") or {}
    return page_props.get("ssrHits", [])


def _extract_company_name(job: dict[str, Any]) -> str | None:
    """Best-effort company name extraction."""
    v5 = job.get("v5_processed_job_data") or {}
    name = v5.get("company_name")
    if name:
        return str(name).strip() or None

    enriched = job.get("enriched_company_data") or {}
    name = enriched.get("name")
    if name:
        return str(name).strip() or None

    # Fallback to board token (e.g., "decagon")
    board = job.get("board_token")
    if board:
        return str(board).strip() or None

    return None


def _extract_location(job: dict[str, Any]) -> str | None:
    """Best-effort location extraction."""
    v5 = job.get("v5_processed_job_data") or {}
    loc = v5.get("formatted_workplace_location")
    if loc:
        return str(loc).strip() or None
    return None


def _extract_remote_type(job: dict[str, Any]) -> str | None:
    """Map HiringCafe workplace_type to our remote_type enum."""
    v5 = job.get("v5_processed_job_data") or {}
    wt = v5.get("workplace_type")
    if not wt:
        return None

    wt_lower = str(wt).lower()
    if wt_lower == "remote":
        return "remote"
    if wt_lower == "hybrid":
        return "hybrid"
    if wt_lower == "onsite":
        return "onsite"
    return None


def _extract_salary(
    job: dict[str, Any],
) -> tuple[str | None, int | None, int | None]:
    """Extract salary info from v5_processed_job_data."""
    v5 = job.get("v5_processed_job_data") or {}
    currency = v5.get("listed_compensation_currency") or ""
    frequency = v5.get("listed_compensation_frequency") or ""

    min_val = v5.get("yearly_min_compensation")
    max_val = v5.get("yearly_max_compensation")

    # Fallback to monthly / weekly / hourly if yearly is missing
    if not _is_valid_number(min_val) and not _is_valid_number(max_val):
        for prefix in ("monthly", "weekly", "hourly", "bi-weekly", "daily"):
            min_val = v5.get(f"{prefix}_min_compensation")
            max_val = v5.get(f"{prefix}_max_compensation")
            if _is_valid_number(min_val) or _is_valid_number(max_val):
                frequency = prefix
                break

    if not _is_valid_number(min_val) and not _is_valid_number(max_val):
        return None, None, None

    parts: list[str] = []
    if _is_valid_number(min_val):
        parts.append(str(min_val))
    if _is_valid_number(max_val):
        parts.append(str(max_val))
    raw = " - ".join(parts)
    if currency:
        raw += f" {currency}"
    if frequency:
        raw += f" / {frequency}"

    salary_min_usd = None
    salary_max_usd = None
    if str(currency).upper() == "USD":
        if _is_valid_number(min_val):
            salary_min_usd = int(float(min_val))
        if _is_valid_number(max_val):
            salary_max_usd = int(float(max_val))

    return raw or None, salary_min_usd, salary_max_usd


def _extract_posted_at(job: dict[str, Any]) -> str | None:
    """Extract ISO-8601 posted date."""
    v5 = job.get("v5_processed_job_data") or {}
    date = v5.get("estimated_publish_date")
    if date:
        return str(date).strip() or None
    return None


def _normalize_job(job: dict[str, Any]) -> dict[str, Any] | None:
    """Map a single HiringCafe API hit to a Job Forager raw record."""
    job_id = str(job.get("id") or "").strip()
    apply_url = str(job.get("apply_url") or "").strip()
    job_info = job.get("job_information") or {}
    title = str(job_info.get("title") or "").strip()

    company = _extract_company_name(job)

    if not title or not company or not apply_url:
        return None

    description = job_info.get("description", "")
    if description:
        description = _strip_html(str(description))

    location = _extract_location(job)
    remote_type = _extract_remote_type(job)
    salary_raw, salary_min_usd, salary_max_usd = _extract_salary(job)
    posted_at = _extract_posted_at(job)

    # Build a hiring.cafe permalink
    job_url = f"{_BASE_URL}/viewjob/{job_id}" if job_id else apply_url

    return {
        "source": "hiringcafe",
        "title": title,
        "company": company,
        "job_url": job_url,
        "location": location,
        "remote_type": remote_type,
        "salary_raw": salary_raw,
        "salary_min_usd": salary_min_usd,
        "salary_max_usd": salary_max_usd,
        "posted_at": posted_at,
        "apply_url": apply_url,
        "external_id": job_id or None,
        "description": description or None,
        "tags": [],
        "metadata": {
            "board_token": job.get("board_token"),
            "source": job.get("source"),
            "source_and_board_token": job.get("source_and_board_token"),
        },
    }


def collect_hiringcafe_jobs(
    search_term: str | None = None,
    location: str | None = None,
    max_results: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch jobs from HiringCafe via Next.js data API.

    Long search terms are automatically sharded into smaller queries.
    Multiple comma-separated locations are searched independently (OR
    logic) and merged (deduplicated by job ID).

    Build IDs are discovered automatically on first use and cached for
    the remainder of the process life-time.
    """
    geo_queries, workplace_types = _parse_location_input(location)

    # Resolve each geo query into a search descriptor.
    # A descriptor is either:
    #   ("geo", wrapper)            – search this location directly
    #   ("city", wrapper, city)     – search parent country, post-filter city
    geo_searches: list[tuple[str, dict[str, Any], str | None]] = []

    for query in geo_queries:
        wrapper = _resolve_location(query)
        if not wrapper:
            continue
        pd = wrapper.get("placeDetail") or {}
        loc_types = pd.get("types") or []

        if "locality" in loc_types:
            # City-level: search at country level, post-filter for city.
            city_name = pd.get("address_components", [{}])[0].get(
                "long_name", query
            )
            country_wrapper = _extract_country_from_wrapper(wrapper)
            if country_wrapper:
                geo_searches.append(("city", country_wrapper, city_name))
            else:
                geo_searches.append(("geo", wrapper, None))
        else:
            geo_searches.append(("geo", wrapper, None))

    shards = _shard_search_term(search_term)
    all_results: list[dict[str, Any]] = []
    seen_job_ids: set[str] = set()

    for shard in shards:
        # 1. Search each geo criterion independently (OR logic)
        for kind, wrapper, city_filter in geo_searches:
            search_state = {"searchQuery": shard, "locations": [wrapper]}
            hits = _fetch_page(search_state)
            for job in hits:
                job_id = str(job.get("id") or "").strip()
                if not job_id or job_id in seen_job_ids:
                    continue
                normalized = _normalize_job(job)
                if normalized is None:
                    continue
                # City post-filter
                if city_filter:
                    job_loc = (normalized.get("location") or "").lower()
                    if city_filter.lower() not in job_loc:
                        continue
                seen_job_ids.add(job_id)
                all_results.append(normalized)
                if max_results is not None and len(all_results) >= max_results:
                    return all_results[:max_results]

        # 2. Search each workplace type independently (OR logic)
        for wt in workplace_types:
            search_state = {"searchQuery": shard, "workplaceTypes": [wt]}
            hits = _fetch_page(search_state)
            for job in hits:
                job_id = str(job.get("id") or "").strip()
                if not job_id or job_id in seen_job_ids:
                    continue
                normalized = _normalize_job(job)
                if normalized is None:
                    continue
                seen_job_ids.add(job_id)
                all_results.append(normalized)
                if max_results is not None and len(all_results) >= max_results:
                    return all_results[:max_results]

        # 3. If no location criteria at all, search globally
        if not geo_searches and not workplace_types:
            search_state = {"searchQuery": shard}
            hits = _fetch_page(search_state)
            for job in hits:
                job_id = str(job.get("id") or "").strip()
                if not job_id or job_id in seen_job_ids:
                    continue
                normalized = _normalize_job(job)
                if normalized is None:
                    continue
                seen_job_ids.add(job_id)
                all_results.append(normalized)
                if max_results is not None and len(all_results) >= max_results:
                    return all_results[:max_results]

    return all_results
