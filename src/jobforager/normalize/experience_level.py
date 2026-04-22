"""Experience level extraction from job titles."""

import re

_KEYWORDS = {
    "intern": -100,
    "internship": -100,
    "trainee": -25,
    "graduate": -25,
    "new grad": -25,
    "entry level": -25,
    "entry-level": -25,
    "junior": -20,
    "jr": -20,
    "associate": -10,
    "i": -15,
    "1": -15,
    "ii": 5,
    "2": 5,
    "iii": 15,
    "3": 5,
    "iv": 15,
    "4": 15,
    "v": 15,
    "5": 15,
    "senior": 20,
    "sr": 20,
    "lead": 30,
    "staff": 30,
    "principal": 40,
    "architect": 15,
    "manager": 15,
    "director": 50,
    "vp": 50,
    "vice president": 50,
    "cto": 50,
    "ceo": 50,
    "chief": 50,
    "head of": 30,
    "distinguished": 40,
    "fellow": 40,
}


def extract_experience_level(title: str) -> str:
    """Classify job title into experience tier."""
    if not title:
        return "unknown"

    title_lower = title.lower()
    score = 0

    for pattern, weight in _KEYWORDS.items():
        if re.search(rf"\b{re.escape(pattern)}\b", title_lower):
            score += weight

    if score < -50:
        return "intern"
    if score <= -5:
        return "entry"
    if score >= 20:
        return "senior"
    return "mid"
