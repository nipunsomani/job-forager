from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from jobforager.search.adzuna import collect_adzuna_jobs
from jobforager.search.ashby import collect_ashby_jobs
from jobforager.search.arbeitnow import collect_arbeitnow_jobs
from jobforager.search.greenhouse import collect_greenhouse_jobs
from jobforager.search.hackernews import collect_hackernews_jobs
from jobforager.search.hiringcafe import collect_hiringcafe_jobs
from jobforager.search.pinpoint import collect_pinpoint_jobs
from jobforager.search.jobspy_source import (
    collect_glassdoor_jobs,
    collect_indeed_jobs,
    collect_linkedin_jobs,
)
from jobforager.search.lever import collect_lever_jobs
from jobforager.search.remoteok import collect_remoteok_jobs
from jobforager.search.remotive import collect_remotive_jobs
from jobforager.search.smartrecruiters import collect_smartrecruiters_jobs
from jobforager.search.twosigma import collect_twosigma_jobs
from jobforager.search.workday import collect_workday_jobs
from jobforager.search.weworkremotely import collect_weworkremotely_jobs
from jobforager.company_lists import get_smartrecruiters_slugs


def _run_with_timeout(
    func: Callable[[], list[dict[str, Any]]],
    timeout: float,
) -> list[dict[str, Any]]:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func)
    try:
        result = future.result(timeout=timeout)
    except Exception:
        executor.shutdown(wait=False)
        raise
    else:
        executor.shutdown(wait=False)
        return result


def _probe_generic(
    func: Callable[[], list[dict[str, Any]]],
    timeout: float,
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        jobs = _run_with_timeout(func, timeout)
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "status": "fail",
            "jobs_found": 0,
            "elapsed_ms": elapsed_ms,
            "error": str(exc),
        }

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return {
        "status": "ok",
        "jobs_found": min(len(jobs), 1),
        "elapsed_ms": elapsed_ms,
    }


def probe_remotive(timeout: float) -> dict[str, Any]:
    return _probe_generic(lambda: collect_remotive_jobs(limit=1), timeout)


def probe_hackernews(timeout: float) -> dict[str, Any]:
    return _probe_generic(lambda: collect_hackernews_jobs(max_comments=1), timeout)


def probe_remoteok(timeout: float) -> dict[str, Any]:
    return _probe_generic(lambda: collect_remoteok_jobs()[:1], timeout)


def probe_arbeitnow(timeout: float) -> dict[str, Any]:
    return _probe_generic(lambda: collect_arbeitnow_jobs()[:1], timeout)


def probe_greenhouse(timeout: float) -> dict[str, Any]:
    return _probe_generic(
        lambda: collect_greenhouse_jobs(max_boards=3, max_workers=1), timeout
    )


def probe_lever(timeout: float) -> dict[str, Any]:
    return _probe_generic(
        lambda: collect_lever_jobs(max_companies=3, max_workers=1), timeout
    )


def probe_ashby(timeout: float) -> dict[str, Any]:
    return _probe_generic(
        lambda: collect_ashby_jobs(max_boards=3, max_workers=1), timeout
    )


def probe_smartrecruiters(timeout: float) -> dict[str, Any]:
    slugs = get_smartrecruiters_slugs()
    if not slugs:
        return {
            "status": "fail",
            "jobs_found": 0,
            "elapsed_ms": 0,
            "error": "no company slugs available",
        }
    return _probe_generic(
        lambda: collect_smartrecruiters_jobs(company_slugs=slugs[:1], max_workers=1),
        timeout,
    )


def probe_workday(timeout: float) -> dict[str, Any]:
    return _probe_generic(
        lambda: collect_workday_jobs(
            max_results_per_company=1, max_companies=1, max_workers=1
        ),
        timeout,
    )


def probe_hiringcafe(timeout: float) -> dict[str, Any]:
    return _probe_generic(lambda: collect_hiringcafe_jobs(max_results=1), timeout)


def probe_linkedin(timeout: float) -> dict[str, Any]:
    return _probe_generic(lambda: collect_linkedin_jobs(results_wanted=1), timeout)


def probe_indeed(timeout: float) -> dict[str, Any]:
    return _probe_generic(lambda: collect_indeed_jobs(results_wanted=1), timeout)


def probe_glassdoor(timeout: float) -> dict[str, Any]:
    return _probe_generic(lambda: collect_glassdoor_jobs(results_wanted=1), timeout)


def probe_weworkremotely(timeout: float) -> dict[str, Any]:
    return _probe_generic(lambda: collect_weworkremotely_jobs()[:1], timeout)


def probe_twosigma(timeout: float) -> dict[str, Any]:
    return _probe_generic(lambda: collect_twosigma_jobs()[:1], timeout)


def probe_adzuna(timeout: float) -> dict[str, Any]:
    return _probe_generic(lambda: collect_adzuna_jobs()[:1], timeout)


def probe_pinpoint(timeout: float) -> dict[str, Any]:
    return _probe_generic(lambda: collect_pinpoint_jobs(max_results=1), timeout)


_PROBE_MAP: dict[str, Callable[[float], dict[str, Any]]] = {
    "remotive": probe_remotive,
    "hackernews": probe_hackernews,
    "remoteok": probe_remoteok,
    "arbeitnow": probe_arbeitnow,
    "greenhouse": probe_greenhouse,
    "lever": probe_lever,
    "ashby": probe_ashby,
    "smartrecruiters": probe_smartrecruiters,
    "workday": probe_workday,
    "hiringcafe": probe_hiringcafe,
    "linkedin": probe_linkedin,
    "indeed": probe_indeed,
    "glassdoor": probe_glassdoor,
    "weworkremotely": probe_weworkremotely,
    "twosigma": probe_twosigma,
    "adzuna": probe_adzuna,
    "pinpoint": probe_pinpoint,
}


def run_health_probe(source: str, timeout: float) -> dict[str, Any]:
    probe = _PROBE_MAP.get(source)
    if probe is None:
        return {
            "status": "fail",
            "jobs_found": 0,
            "elapsed_ms": 0,
            "error": f"unknown source {source}",
        }
    return probe(timeout)


def all_sources() -> list[str]:
    return list(_PROBE_MAP.keys())
