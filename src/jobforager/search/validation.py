"""URL validation utilities for job records."""

import ssl
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from jobforager.models.job_record import JobRecord

__all__ = [
    "validate_job_url",
    "validate_job_urls",
]


def validate_job_url(job_url: str, timeout: float = 5.0) -> dict[str, Any]:
    """
    Validate a job URL by making a HEAD request (falling back to GET).

    Args:
        job_url: The URL to validate.
        timeout: Request timeout in seconds.

    Returns:
        Dict with keys: status ("ok" | "unreachable" | "error"),
        http_code (int | None), message (str).
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(job_url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            http_code = response.status
            if 200 <= http_code < 400:
                return {"status": "ok", "http_code": http_code, "message": "URL is reachable"}
            return {"status": "unreachable", "http_code": http_code, "message": f"HTTP {http_code}"}
    except urllib.error.HTTPError as e:
        if e.code == 405:
            req = urllib.request.Request(job_url, method="GET")
            req.add_header("User-Agent", "Mozilla/5.0")
            try:
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                    http_code = response.status
                    if 200 <= http_code < 400:
                        return {"status": "ok", "http_code": http_code, "message": "URL is reachable"}
                    return {"status": "unreachable", "http_code": http_code, "message": f"HTTP {http_code}"}
            except urllib.error.HTTPError as e2:
                return {"status": "unreachable", "http_code": e2.code, "message": f"HTTP error: {e2.code}"}
        return {"status": "unreachable", "http_code": e.code, "message": f"HTTP error: {e.code}"}
    except urllib.error.URLError as e:
        return {"status": "error", "http_code": None, "message": f"URL error: {e.reason}"}
    except TimeoutError:
        return {"status": "error", "http_code": None, "message": "Request timed out"}


def validate_job_urls(jobs: list[JobRecord], timeout: float = 5.0) -> list[dict[str, Any]]:
    """
    Validate job URLs for a list of JobRecord objects.

    Args:
        jobs: List of JobRecord objects.
        timeout: Request timeout in seconds.

    Returns:
        List of result dicts (same order as input jobs).
    """
    results = []
    for i, job in enumerate(jobs):
        results.append(validate_job_url(job.job_url, timeout=timeout))
        if i < len(jobs) - 1:
            time.sleep(0.3)
    return results
