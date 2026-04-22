from __future__ import annotations

from collections import Counter
from typing import Any

from jobforager.models import JobRecord


def build_search_summary(
    records: list[JobRecord],
    dedupe_keys: list[str],
    active_sources: list[str],
    validated_count: int,
    invalid_count: int,
) -> list[str]:
    unique = len(set(dedupe_keys))
    duplicates = len(records) - unique

    source_counts = Counter(job.source for job in records)

    lines: list[str] = []
    lines.append("---")
    lines.append(f"summary total_records={len(records)}")
    lines.append(f"summary unique={unique} duplicates={duplicates}")
    lines.append(f"summary sources={','.join(active_sources)}")
    lines.append(f"summary validated={validated_count} invalid={invalid_count}")
    if source_counts:
        by_source = " ".join(f"{k}={v}" for k, v in sorted(source_counts.items()))
        lines.append(f"summary by_source {by_source}")
    return lines


def build_summary(
    normalized_records: list[JobRecord],
    dedupe_keys: list[str],
    active_sources: list[str],
) -> list[str]:
    unique = len(set(dedupe_keys))
    duplicates = len(normalized_records) - unique

    source_counts = Counter(job.source for job in normalized_records)
    remote_type_counts = Counter(
        job.remote_type for job in normalized_records if job.remote_type is not None
    )

    lines: list[str] = []
    lines.append("---")
    lines.append(f"summary total_records={len(normalized_records)}")
    lines.append(f"summary unique={unique} duplicates={duplicates}")
    lines.append(f"summary sources={','.join(active_sources)}")
    if source_counts:
        by_source = " ".join(f"{k}={v}" for k, v in sorted(source_counts.items()))
        lines.append(f"summary by_source {by_source}")
    if remote_type_counts:
        by_remote = " ".join(f"{k}={v}" for k, v in sorted(remote_type_counts.items()))
        lines.append(f"summary by_remote_type {by_remote}")
    return lines
