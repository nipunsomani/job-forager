from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jobforager.collectors import CollectorRegistry, load_raw_records_from_file
from jobforager.config import load_candidate_profile
from jobforager.exporters import (
    write_normalized_csv,
    write_normalized_json,
    write_normalized_markdown,
)
from jobforager.formatters import build_summary, build_search_summary
from jobforager.models import JobRecord
from jobforager.normalize import build_dedupe_key, filter_jobs, normalize_raw_job_record
from jobforager.samples import sample_raw_records
from jobforager.cli.pipeline import run_search_pipeline
from jobforager.search.health_probes import all_sources, run_health_probe


def _print_help_status() -> None:
    print("job-forager Phase 1.2 ingestion foundation is ready.")
    print("Dry-run config/normalize/dedupe flow is available.")
    print("No real collectors/ATS/scoring/apply logic implemented yet.")


def _run_validate_command(args: argparse.Namespace) -> int:
    profile_path = Path(args.profile)
    try:
        profile = load_candidate_profile(profile_path)
    except Exception as exc:
        print(f"validate error: {exc}")
        return 1

    print("job-forager validate")
    print(f"profile={profile_path}")
    print(f"profile_status=ok")
    print(
        "profile_summary "
        f"titles={len(profile.target_titles)} "
        f"skills={len(profile.skills)} "
        f"locations={len(profile.locations)} "
        f"remote_preference={profile.remote_preference}"
    )
    if profile.salary_floor_usd is not None:
        print(f"salary_floor_usd={profile.salary_floor_usd}")
    enabled_sources = [
        name for name, on in sorted(profile.source_toggles.items()) if on
    ]
    print(f"sources_enabled={','.join(enabled_sources) or 'none'}")
    filters_active = []
    if profile.target_titles:
        filters_active.append("titles")
    if profile.skills:
        filters_active.append("skills")
    if profile.locations:
        filters_active.append("locations")
    if profile.salary_floor_usd is not None:
        filters_active.append("salary_floor")
    if profile.remote_preference != "any":
        filters_active.append("remote_preference")
    print(f"filters_active={','.join(filters_active) or 'none'}")
    return 0


def _run_hunt_command(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("Phase 1.2 currently supports `hunt --dry-run` only.")
        return 0

    profile_path = Path(args.profile)
    profile = load_candidate_profile(profile_path)

    registry = CollectorRegistry()
    registry.register("sample", sample_raw_records)

    enabled_sources = dict(profile.source_toggles)

    if args.records:
        registry.register(
            "file", lambda: load_raw_records_from_file(args.records)
        )
        enabled_sources["file"] = True

    errors: dict[str, str] = {}
    raw_records = registry.collect(enabled_sources, errors=errors)

    if not raw_records and args.records is None:
        raw_records = sample_raw_records()
        enabled_sources.setdefault("sample", True)

    normalized_records: list[JobRecord] = []
    normalization_errors: list[str] = []
    for record in raw_records:
        try:
            normalized_records.append(normalize_raw_job_record(record))
        except Exception as exc:
            normalization_errors.append(str(exc))

    filtered_records = filter_jobs(normalized_records, profile)
    dedupe_keys = [build_dedupe_key(record) for record in filtered_records]
    unique_keys = len(set(dedupe_keys))

    active_sources = [
        name for name, on in enabled_sources.items() if on and name in registry.available_sources()
    ]
    if not raw_records and "sample" not in active_sources:
        active_sources.append("sample")

    print("job-forager dry run")
    print(f"profile={profile_path}")
    print(
        "profile_summary "
        f"titles={len(profile.target_titles)} "
        f"skills={len(profile.skills)} "
        f"locations={len(profile.locations)} "
        f"remote_preference={profile.remote_preference}"
    )
    print(
        f"sources_enabled={','.join(active_sources)} "
        f"records={len(filtered_records)} unique_keys={unique_keys} "
        f"duplicates={len(filtered_records) - unique_keys}"
    )

    for index, (job, dedupe_key) in enumerate(
        zip(filtered_records, dedupe_keys, strict=True), start=1
    ):
        print(f"{index}. {job.title} @ {job.company} [{job.source}]")
        print(f"   dedupe_key={dedupe_key}")

    if normalization_errors:
        print(f"skipped_records={len(normalization_errors)}")
        for index, msg in enumerate(normalization_errors[:3], start=1):
            print(f"  {index}. {msg}")

    for line in build_summary(filtered_records, dedupe_keys, active_sources):
        print(line)

    if errors:
        print("---")
        for name, msg in sorted(errors.items()):
            print(f"error source={name} {msg}")

    if args.output_json:
        print(f"export_json records={len(filtered_records)} path={args.output_json}")
        write_normalized_json(filtered_records, dedupe_keys, args.output_json)
        print(f"wrote_json={args.output_json}")

    if args.output_csv:
        print(f"export_csv records={len(filtered_records)} path={args.output_csv}")
        write_normalized_csv(filtered_records, dedupe_keys, args.output_csv)
        print(f"wrote_csv={args.output_csv}")

    has_skipped = bool(normalization_errors)
    has_collector_errors = bool(errors)
    if has_skipped and has_collector_errors:
        status = "completed_with_skipped_and_errors"
    elif has_skipped:
        status = "completed_with_skipped_records"
    elif has_collector_errors:
        status = "completed_with_collector_errors"
    else:
        status = "completed_clean"
    print(f"status={status}")

    return 0


def _run_search_command(args: argparse.Namespace) -> int:
    profile = None
    if args.profile:
        profile_path = Path(args.profile)
        try:
            profile = load_candidate_profile(profile_path)
        except Exception as exc:
            print(f"search error: failed to load profile: {exc}")
            return 1

    keywords = None
    if args.keywords:
        keywords = [kw.strip() for kw in args.keywords.split(",") if kw.strip()]

    excluded = None
    if args.exclude:
        excluded = [kw.strip() for kw in args.exclude.split(",") if kw.strip()]

    title_keywords = None
    if args.title_keywords:
        title_keywords = [kw.strip() for kw in args.title_keywords.split(",") if kw.strip()]

    desc_keywords = None
    if args.desc_keywords:
        desc_keywords = [kw.strip() for kw in args.desc_keywords.split(",") if kw.strip()]

    since_dt: datetime | None = None
    if args.since:
        try:
            since_dt = datetime.strptime(args.since, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            print("search error: --since must be in YYYY-MM-DD format.")
            return 1

    last_duration: timedelta | None = None
    if args.last_duration:
        last_str = args.last_duration.strip().lower()
        if last_str.endswith("h"):
            try:
                hours = int(last_str[:-1])
                last_duration = timedelta(hours=hours)
            except ValueError:
                print("search error: --last must be like 24h, 7d, 30d.")
                return 1
        elif last_str.endswith("d"):
            try:
                days = int(last_str[:-1])
                last_duration = timedelta(days=days)
            except ValueError:
                print("search error: --last must be like 24h, 7d, 30d.")
                return 1
        else:
            print("search error: --last must be like 24h, 7d, 30d.")
            return 1

    _ALL_SOURCES = [
        "remotive", "hackernews", "remoteok", "arbeitnow",
        "greenhouse", "lever", "ashby", "smartrecruiters",
        "workday", "hiringcafe",
        "linkedin", "indeed", "glassdoor",
        "weworkremotely",
        "adzuna",
    ]

    source_names = [s.strip() for s in args.sources.split(",") if s.strip()]
    if source_names == ["all"]:
        source_names = _ALL_SOURCES[:]
    elif profile is not None and args.sources == "remotive,hackernews":
        # Default sources not overridden; use profile toggles
        toggled = [
            name for name in _ALL_SOURCES
            if profile.source_toggles.get(f"enable_{name}", True)
        ]
        if toggled:
            source_names = toggled

    workers = max(1, args.workers)

    result = run_search_pipeline(
        source_names=source_names,
        workers=workers,
        profile=profile,
        keywords=keywords,
        excluded=excluded,
        location_query=args.location,
        since=since_dt,
        last_duration=last_duration,
        level=args.level,
        hide_recruiters=args.hide_recruiters,
        title_keywords=title_keywords,
        desc_keywords=desc_keywords,
        db_path=args.db_path,
        since_last_run=args.since_last_run,
        no_validate=args.no_validate,
    )

    active_sources = result["active_sources"]
    unique_records = result["records"]
    unique_keys = result["keys"]
    validated_count = result["validated_count"]
    invalid_count = result["invalid_count"]
    normalization_errors = result["normalization_errors"]
    errors = result["collector_errors"]

    print("job-forager search")
    print(f"sources_queried={','.join(active_sources) or 'none'}")
    print(f"fetched={result['raw_count']}")
    print(f"matched={result['unique_count']}")
    print(f"validated={validated_count}")
    print(f"invalid={invalid_count}")
    print(f"unique={result['unique_count']}")
    if result["duplicate_count"]:
        print(f"duplicates={result['duplicate_count']}")
    if args.since_last_run:
        print(f"new_since_last_run={result['new_since_last_run']}")

    def _safe(value: str | None) -> str:
        if not value:
            return ""
        return value.encode("ascii", errors="replace").decode("ascii")

    for index, job in enumerate(unique_records, start=1):
        print(
            f"{index}. {_safe(job.title)} @ {_safe(job.company)} [{job.source}]"
        )
        print(f"   url={job.job_url}")
        if job.location:
            print(f"   location={_safe(job.location)}")
        if job.posted_at:
            print(f"   posted_at={job.posted_at.isoformat()}")
        print(f"   validated={job.metadata.get('validated', 'unknown')}")

    if normalization_errors:
        print(f"skipped_records={len(normalization_errors)}")
        for index, msg in enumerate(normalization_errors[:3], start=1):
            print(f"  {index}. {msg}")

    for line in build_search_summary(
        unique_records, unique_keys, active_sources, validated_count, invalid_count
    ):
        print(line)

    if errors:
        print("---")
        for name, msg in sorted(errors.items()):
            print(f"error source={name} {msg}")

    if args.output_json:
        print(
            f"export_json records={len(unique_records)} path={args.output_json}"
        )
        write_normalized_json(unique_records, unique_keys, args.output_json)
        print(f"wrote_json={args.output_json}")

    if args.output_csv:
        print(
            f"export_csv records={len(unique_records)} path={args.output_csv}"
        )
        write_normalized_csv(unique_records, unique_keys, args.output_csv)
        print(f"wrote_csv={args.output_csv}")

    if args.output_md:
        print(
            f"export_md records={len(unique_records)} path={args.output_md}"
        )
        write_normalized_markdown(unique_records, unique_keys, args.output_md)
        print(f"wrote_md={args.output_md}")

    has_skipped = bool(normalization_errors)
    has_collector_errors = bool(errors)
    if has_skipped and has_collector_errors:
        status = "completed_with_skipped_and_errors"
    elif has_skipped:
        status = "completed_with_skipped_records"
    elif has_collector_errors:
        status = "completed_with_collector_errors"
    else:
        status = "completed_clean"
    print(f"status={status}")

    return 0


def _run_health_command(args: argparse.Namespace) -> int:
    source_names = [s.strip() for s in args.sources.split(",") if s.strip()]
    if source_names == ["all"]:
        source_names = all_sources()

    timeout = float(args.timeout)
    ok_count = 0
    fail_count = 0
    results: list[tuple[str, dict[str, Any]]] = []
    for source in source_names:
        result = run_health_probe(source, timeout)
        results.append((source, result))
        if result["status"] == "ok":
            ok_count += 1
        else:
            fail_count += 1

    for source, result in results:
        line = (
            f"source={source} status={result['status']} "
            f"jobs_found={result.get('jobs_found', 0)} "
            f"elapsed_ms={result.get('elapsed_ms', 0)}"
        )
        error = result.get("error")
        if error:
            line += f' error="{error}"'
        print(line)

    total = len(source_names)
    print(f"summary total={total} ok={ok_count} fail={fail_count}")
    return 0 if fail_count == 0 else 1
