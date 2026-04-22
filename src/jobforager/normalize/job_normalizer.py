from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, TypedDict

from jobforager.models import JobRecord

from .ats_detector import detect_ats_from_record


class RawJobRecord(TypedDict, total=False):
    source: str
    title: str
    company: str
    job_url: str
    location: str | None
    remote_type: str | None
    salary_raw: str | None
    salary_min_usd: int | str | None
    salary_max_usd: int | str | None
    posted_at: datetime | str | None
    apply_url: str | None
    external_id: str | None
    description: str | None
    tags: list[str] | tuple[str, ...] | str | None
    metadata: dict[str, Any] | None


_KNOWN_FIELDS = {
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
    "external_id",
    "description",
    "tags",
    "metadata",
}
_REMOTE_TYPE_ALIASES = {
    "on-site": "onsite",
    "on_site": "onsite",
    "remote_only": "remote",
}
_VALID_REMOTE_TYPES = {"remote", "hybrid", "onsite", "unknown"}


def normalize_raw_job_record(raw_record: Mapping[str, Any]) -> JobRecord:
    """Map one raw source record into canonical JobRecord."""

    if not isinstance(raw_record, Mapping):
        raise TypeError("Raw job record must be a mapping.")

    metadata = _normalize_metadata(raw_record.get("metadata"))
    for key, value in raw_record.items():
        if key not in _KNOWN_FIELDS:
            metadata.setdefault(key, value)

    ats_platform = detect_ats_from_record(dict(raw_record))

    return JobRecord(
        source=_required_string(raw_record, "source"),
        title=_required_string(raw_record, "title"),
        company=_required_string(raw_record, "company"),
        job_url=_required_string(raw_record, "job_url"),
        location=_optional_string(raw_record.get("location"), "location"),
        remote_type=_normalize_remote_type(raw_record.get("remote_type")),
        salary_raw=_optional_string(raw_record.get("salary_raw"), "salary_raw"),
        salary_min_usd=_optional_int(raw_record.get("salary_min_usd"), "salary_min_usd"),
        salary_max_usd=_optional_int(raw_record.get("salary_max_usd"), "salary_max_usd"),
        posted_at=_normalize_posted_at(raw_record.get("posted_at")),
        apply_url=_optional_string(raw_record.get("apply_url"), "apply_url"),
        external_id=_optional_string(raw_record.get("external_id"), "external_id"),
        ats_platform=ats_platform,
        description=_optional_string(raw_record.get("description"), "description"),
        tags=_normalize_tags(raw_record.get("tags")),
        metadata=metadata,
    )


def _required_string(raw_record: Mapping[str, Any], field_name: str) -> str:
    value = raw_record.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required field '{field_name}' in raw job record.")
    return value.strip()


def _optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Expected '{field_name}' to be a string.")

    normalized = value.strip()
    return normalized or None


def _optional_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"Expected '{field_name}' to be an integer.")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.strip().replace(",", "")
        if not normalized:
            return None
        try:
            return int(normalized)
        except ValueError as exc:
            raise ValueError(f"Expected '{field_name}' to be an integer.") from exc
    raise ValueError(f"Expected '{field_name}' to be an integer.")


def _normalize_remote_type(value: Any) -> str | None:
    raw = _optional_string(value, "remote_type")
    if raw is None:
        return None

    normalized = _REMOTE_TYPE_ALIASES.get(raw.lower(), raw.lower())
    if normalized not in _VALID_REMOTE_TYPES:
        return "unknown"
    return normalized


def _normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        normalized = value.strip()
        return [normalized] if normalized else []
    if isinstance(value, (list, tuple, set)):
        tags: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str):
                raise ValueError(
                    f"Expected tags[{index}] to be a string, got {type(item).__name__}."
                )
            normalized = item.strip()
            if normalized:
                tags.append(normalized)
        return tags
    raise ValueError("Expected 'tags' to be a string or list of strings.")


def _normalize_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("Expected 'metadata' to be a mapping.")
    return dict(value)


def _normalize_posted_at(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        iso_value = normalized.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(iso_value)
        except ValueError:
            return None
    return None
