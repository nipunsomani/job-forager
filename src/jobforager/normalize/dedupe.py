from __future__ import annotations

from hashlib import sha256

from jobforager.models import JobRecord


def build_dedupe_key(job: JobRecord) -> str:
    """Build a deterministic dedupe key for one canonical job record."""

    source = _normalize_text(job.source)
    external_id = _normalize_text(job.external_id)
    if external_id:
        return f"{source}|external_id|{external_id}"

    fingerprint_input = "|".join(
        [
            _normalize_text(job.source),
            _normalize_text(job.title),
            _normalize_text(job.company),
            _normalize_text(job.job_url),
        ]
    )
    digest = sha256(fingerprint_input.encode("utf-8")).hexdigest()
    return f"{source}|fingerprint|{digest}"


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().lower().split())
