"""Recruiter company detection heuristics."""

_RECRUITER_TERMS = [
    "recruiting",
    "recruiter",
    "recruitment",
    "staffing",
    "talent",
    "talenthub",
    "talentgroup",
    "placement",
    "agency",
]


def is_recruiter_company(company: str) -> bool:
    """Return True if company name matches recruiter heuristic."""
    company_lower = company.lower()
    return any(term in company_lower for term in _RECRUITER_TERMS)
