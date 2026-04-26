from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Callable

from jobforager.collectors import CollectorRegistry
from jobforager.models import JobRecord, CandidateProfile
from jobforager.normalize import build_dedupe_key, filter_jobs, normalize_raw_job_record
from jobforager.search import apply_search_filters
from jobforager.search.adzuna import collect_adzuna_jobs
from jobforager.search.ashby import collect_ashby_jobs
from jobforager.search.arbeitnow import collect_arbeitnow_jobs
from jobforager.search.greenhouse import collect_greenhouse_jobs
from jobforager.search.hackernews import collect_hackernews_jobs
from jobforager.search.hiringcafe import collect_hiringcafe_jobs
from jobforager.search.jobspy_source import (
    collect_glassdoor_jobs,
    collect_indeed_jobs,
    collect_linkedin_jobs,
)
from jobforager.search.lever import collect_lever_jobs
from jobforager.search.remoteok import collect_remoteok_jobs
from jobforager.search.remotive import collect_remotive_jobs
from jobforager.search.smartrecruiters import collect_smartrecruiters_jobs
from jobforager.search.workday import collect_workday_jobs
from jobforager.search.weworkremotely import collect_weworkremotely_jobs
from jobforager.search.validation import validate_job_url
from jobforager.storage import JobStore

logger = logging.getLogger("jobforager.pipeline")


def build_registry(
    source_names: list[str],
    workers: int,
    search_term: str | None = None,
    location_query: str | None = None,
) -> tuple[CollectorRegistry, dict[str, bool]]:
    registry = CollectorRegistry()
    enabled: dict[str, bool] = {name: True for name in source_names}

    config: dict[str, Callable[[], list[dict[str, Any]]]] = {
        "remotive": collect_remotive_jobs,
        "hackernews": collect_hackernews_jobs,
        "remoteok": collect_remoteok_jobs,
        "arbeitnow": collect_arbeitnow_jobs,
        "greenhouse": lambda: collect_greenhouse_jobs(max_boards=None, max_workers=workers),
        "lever": lambda: collect_lever_jobs(max_companies=None, max_workers=workers),
        "ashby": lambda: collect_ashby_jobs(max_boards=None, max_workers=workers),
        "smartrecruiters": lambda: collect_smartrecruiters_jobs(max_workers=workers),
        "workday": lambda: collect_workday_jobs(
            max_results_per_company=None, max_workers=workers
        ),
        "hiringcafe": lambda: collect_hiringcafe_jobs(
            search_term=search_term, location=location_query
        ),
        "linkedin": lambda: collect_linkedin_jobs(
            search_term=search_term, location=location_query
        ),
        "indeed": lambda: collect_indeed_jobs(
            search_term=search_term, location=location_query
        ),
        "glassdoor": lambda: collect_glassdoor_jobs(
            search_term=search_term, location=location_query
        ),
        "weworkremotely": collect_weworkremotely_jobs,
        "adzuna": lambda: collect_adzuna_jobs(
            search_term=search_term, location=location_query
        ),
    }

    for name in enabled:
        if name in config:
            registry.register(name, config[name])

    return registry, enabled


def normalize_records(raw_records: list[dict[str, Any]]) -> tuple[list[JobRecord], list[str]]:
    normalized: list[JobRecord] = []
    errors: list[str] = []
    for record in raw_records:
        try:
            normalized.append(normalize_raw_job_record(record))
        except Exception as exc:
            errors.append(str(exc))
    return normalized, errors


def dedupe_records(records: list[JobRecord]) -> tuple[list[JobRecord], list[str]]:
    dedupe_keys = [build_dedupe_key(record) for record in records]
    unique_key_set: set[str] = set()
    seen_urls: set[str] = set()
    unique_records: list[JobRecord] = []
    unique_keys: list[str] = []
    for job, key in zip(records, dedupe_keys, strict=True):
        if key in unique_key_set:
            continue
        url_key = job.job_url.strip().lower().rstrip("/")
        if url_key in seen_urls:
            continue
        unique_key_set.add(key)
        seen_urls.add(url_key)
        unique_records.append(job)
        unique_keys.append(key)
    return unique_records, unique_keys


_SKIP_VALIDATION_SOURCES = {"weworkremotely", "hiringcafe"}


def validate_records(records: list[JobRecord]) -> tuple[int, int]:
    validated_count = 0
    invalid_count = 0
    for job in records:
        if job.source in _SKIP_VALIDATION_SOURCES:
            job.metadata["validated"] = "skipped"
            job.metadata["http_code"] = None
            validated_count += 1
            continue
        result = validate_job_url(job.job_url)
        job.metadata["validated"] = result["status"]
        job.metadata["http_code"] = result.get("http_code")
        if result["status"] == "ok":
            validated_count += 1
        else:
            invalid_count += 1
    return validated_count, invalid_count


def run_search_pipeline(
    source_names: list[str],
    workers: int,
    profile: CandidateProfile | None,
    keywords: list[str] | None,
    excluded: list[str] | None,
    location_query: str | None,
    since: datetime | None,
    last_duration: timedelta | None,
    level: str | None,
    hide_recruiters: bool,
    title_keywords: list[str] | None = None,
    desc_keywords: list[str] | None = None,
    db_path: str | None = None,
    since_last_run: bool = False,
    no_validate: bool = False,
) -> dict[str, Any]:
    search_term = " ".join(keywords) if keywords else None
    if search_term is None and title_keywords:
        search_term = " ".join(title_keywords)
    if search_term is None and desc_keywords:
        search_term = " ".join(desc_keywords)

    registry, enabled = build_registry(
        source_names, workers, search_term=search_term, location_query=location_query
    )
    errors: dict[str, str] = {}
    raw_records = registry.collect_concurrent(
        enabled, errors=errors, max_workers=workers
    )

    normalized, normalization_errors = normalize_records(raw_records)

    filtered = normalized
    if profile is not None:
        filtered = filter_jobs(filtered, profile)

    filtered = apply_search_filters(
        filtered,
        keywords=keywords,
        excluded=excluded,
        location_query=location_query,
        since=since,
        last_duration=last_duration,
        level=level,
        hide_recruiters=hide_recruiters,
        title_keywords=title_keywords,
        desc_keywords=desc_keywords,
    )

    active_sources = [
        name for name in source_names if name in registry.available_sources()
    ]

    store: JobStore | None = None
    db_path_used: str | None = None
    new_since_last_run = 0

    if db_path or since_last_run:
        store = JobStore(db_path)
        db_path_used = store.path

    if store is not None:
        store.upsert_jobs(raw_records)

        if since_last_run:
            last_run = store.get_last_run_time()
            if last_run is not None:
                new_db_jobs = store.get_jobs_since(last_run)
                new_urls = {j["job_url"] for j in new_db_jobs}
                filtered = [job for job in filtered if job.job_url in new_urls]

    unique_records, unique_keys = dedupe_records(filtered)
    if not no_validate:
        validated_count, invalid_count = validate_records(unique_records)
    else:
        validated_count = 0
        invalid_count = 0
        for job in unique_records:
            job.metadata["validated"] = "skipped"
            job.metadata["http_code"] = None

    if store is not None:
        if since_last_run:
            new_since_last_run = len(unique_records)
        store.record_run(
            sources=active_sources,
            keywords=",".join(keywords) if keywords else None,
            new_jobs_count=new_since_last_run,
        )

    source_counts = Counter(job.source for job in unique_records)

    return {
        "raw_count": len(raw_records),
        "normalized_count": len(normalized),
        "filtered_count": len(filtered),
        "unique_count": len(unique_records),
        "duplicate_count": len(filtered) - len(unique_records),
        "validated_count": validated_count,
        "invalid_count": invalid_count,
        "active_sources": active_sources,
        "source_counts": dict(source_counts),
        "records": unique_records,
        "keys": unique_keys,
        "normalization_errors": normalization_errors,
        "collector_errors": errors,
        "new_since_last_run": new_since_last_run,
        "db_path": db_path_used,
    }
