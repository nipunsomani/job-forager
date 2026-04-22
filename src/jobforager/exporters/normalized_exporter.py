from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from jobforager.models import JobRecord


def write_normalized_json(
    records: list[JobRecord],
    dedupe_keys: list[str],
    path: str | Path,
) -> None:
    """Write normalized records with dedupe keys to a JSON file."""
    path = Path(path)
    items: list[dict[str, Any]] = []
    for record, dedupe_key in zip(records, dedupe_keys, strict=True):
        item = _record_to_dict(record)
        item["dedupe_key"] = dedupe_key
        items.append(item)
    path.write_text(
        json.dumps(items, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_normalized_csv(
    records: list[JobRecord],
    dedupe_keys: list[str],
    path: str | Path,
) -> None:
    """Write normalized records with dedupe keys to a CSV file."""
    path = Path(path)
    if not records:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = [
        "dedupe_key",
        "source",
        "title",
        "company",
        "job_url",
        "location",
        "remote_type",
        "salary_raw",
        "salary_min_usd",
        "salary_max_usd",
        "posted_at",
        "apply_url",
        "ats_platform",
        "description",
        "tags",
        "external_id",
        "metadata",
    ]

    rows: list[dict[str, Any]] = []
    for record, dedupe_key in zip(records, dedupe_keys, strict=True):
        item = _record_to_dict(record)
        item["dedupe_key"] = dedupe_key
        item["posted_at"] = item["posted_at"] if item["posted_at"] else ""
        item["tags"] = "|".join(item["tags"]) if item["tags"] else ""
        item["metadata"] = json.dumps(item["metadata"]) if item["metadata"] else ""
        rows.append(item)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _record_to_dict(record: JobRecord) -> dict[str, Any]:
    result = asdict(record)
    if result.get("posted_at") and isinstance(result["posted_at"], datetime):
        result["posted_at"] = result["posted_at"].isoformat()
    return result
