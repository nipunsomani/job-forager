from __future__ import annotations

COUNTRY_ALIASES: dict[str, list[str]] = {
    "uk": ["uk", "united kingdom", "gb", "britain", "england", "scotland", "wales", "northern ireland"],
    "us": ["us", "usa", "united states", "america"],
    "canada": ["canada", "ca"],
    "germany": ["germany", "de", "deutschland"],
    "france": ["france", "fr"],
    "india": ["india", "in"],
    "australia": ["australia", "au"],
    "netherlands": ["netherlands", "nl", "holland"],
    "ireland": ["ireland", "ie"],
    "switzerland": ["switzerland", "ch"],
    "spain": ["spain", "es"],
    "italy": ["italy", "it"],
    "poland": ["poland", "pl"],
    "brazil": ["brazil", "br"],
    "singapore": ["singapore", "sg"],
    "israel": ["israel", "il"],
}

CITY_TO_COUNTRY: dict[str, list[str]] = {
    "london": ["uk"],
    "manchester": ["uk"],
    "birmingham": ["uk"],
    "leeds": ["uk"],
    "glasgow": ["uk"],
    "edinburgh": ["uk"],
    "bristol": ["uk"],
    "liverpool": ["uk"],
    "nottingham": ["uk"],
    "sheffield": ["uk"],
    "cardiff": ["uk"],
    "belfast": ["uk"],
    "new york": ["us"],
    "san francisco": ["us"],
    "los angeles": ["us"],
    "chicago": ["us"],
    "boston": ["us"],
    "austin": ["us"],
    "seattle": ["us"],
    "washington": ["us"],
    "miami": ["us"],
    "denver": ["us"],
    "dallas": ["us"],
    "toronto": ["canada"],
    "vancouver": ["canada"],
    "montreal": ["canada"],
    "berlin": ["germany"],
    "munich": ["germany"],
    "hamburg": ["germany"],
    "paris": ["france"],
    "lyon": ["france"],
    "mumbai": ["india"],
    "bangalore": ["india"],
    "delhi": ["india"],
    "hyderabad": ["india"],
    "pune": ["india"],
    "chennai": ["india"],
    "sydney": ["australia"],
    "melbourne": ["australia"],
    "amsterdam": ["netherlands"],
    "dublin": ["ireland"],
    "zurich": ["switzerland"],
    "geneva": ["switzerland"],
    "madrid": ["spain"],
    "barcelona": ["spain"],
    "milan": ["italy"],
    "rome": ["italy"],
    "warsaw": ["poland"],
    "krakow": ["poland"],
    "sao paulo": ["brazil"],
}


def _tokenize(location: str) -> list[str]:
    """Split location string into clean tokens."""
    import re
    # Split on common delimiters
    parts = re.split(r"[,;|\/\-]+", location)
    tokens = []
    for part in parts:
        token = part.strip().lower()
        if token:
            tokens.append(token)
    return tokens


def normalize_location(location: str | None, expand_cities: bool = True) -> set[str]:
    """Normalize a location string into canonical tokens."""
    if not location:
        return set()

    tokens = _tokenize(location)
    canonical: set[str] = set()

    for token in tokens:
        # Check for remote
        if "remote" in token:
            canonical.add("remote")

        # Check country aliases
        for country, aliases in COUNTRY_ALIASES.items():
            if token in aliases:
                canonical.add(country)

        # Check city-to-country mapping
        if expand_cities:
            for city, countries in CITY_TO_COUNTRY.items():
                if city in token:
                    canonical.update(countries)
                    canonical.add(city)

        # Add the raw token as a fallback (cleaned)
        canonical.add(token)

    return canonical


def location_matches(job_location: str | None, query_locations: list[str]) -> bool:
    """Return True if job location matches any query location.

    Rules:
    - None job_location always matches.
    - Empty query_locations always match.
    - Plain remote (only token is 'remote') matches any non-empty query.
    - Otherwise, there must be an intersection of canonical tokens.
    """
    if job_location is None:
        return True
    if not query_locations:
        return True

    job_tokens = normalize_location(job_location, expand_cities=True)
    query_tokens: set[str] = set()
    for ql in query_locations:
        query_tokens.update(normalize_location(ql, expand_cities=False))

    if job_tokens & query_tokens:
        return True

    # Plain remote inclusion: if job location has no country info, include it
    if job_tokens == {"remote"}:
        return True

    return False
