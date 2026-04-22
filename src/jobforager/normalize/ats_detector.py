"""ATS platform detection from job URLs."""

from __future__ import annotations

from typing import Any

_ATS_PATTERNS: list[tuple[str, str]] = [
    ("greenhouse", "boards.greenhouse.io"),
    ("greenhouse", "job-boards.greenhouse.io"),
    ("lever", "jobs.lever.co"),
    ("lever", "api.lever.co"),
    ("ashby", "jobs.ashbyhq.com"),
    ("ashby", "api.ashbyhq.com"),
    ("workday", "myworkdayjobs.com"),
    ("workday", "wd1.myworkdayjobs.com"),
    ("workday", "wd2.myworkdayjobs.com"),
    ("workday", "wd3.myworkdayjobs.com"),
    ("workday", "wd5.myworkdayjobs.com"),
    ("rippling", "ats.rippling.com"),
    ("workable", "apply.workable.com"),
    ("workable", "workable.com"),
    ("bamboohr", "bamboohr.com/careers"),
    ("smartrecruiters", "smartrecruiters.com"),
    ("greenhouse", "greenhouse.io"),
]


def detect_ats_platform(url: str | None) -> str | None:
    """Detect the ATS platform from a job URL."""
    if not url:
        return None
    url_lower = url.lower()
    for platform, pattern in _ATS_PATTERNS:
        if pattern in url_lower:
            return platform
    return None


def detect_ats_from_record(raw_record: dict[str, Any]) -> str | None:
    """Detect ATS platform from a raw job record.

    Checks job_url first, then apply_url, then falls back to source field.
    """
    for key in ("job_url", "apply_url"):
        value = raw_record.get(key)
        if isinstance(value, str):
            detected = detect_ats_platform(value)
            if detected:
                return detected
    source = raw_record.get("source")
    if source in ("greenhouse", "lever", "ashby", "workday", "rippling", "workable"):
        return source
    return None
