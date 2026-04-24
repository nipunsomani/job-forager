from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from jobforager.models import JobRecord


def write_normalized_markdown(
    records: list[JobRecord],
    keys: list[str],
    output_path: str,
    header_title: str = "Job Search Results",
) -> None:
    """Write normalized records as a Markdown file."""
    path = Path(output_path)
    lines: list[str] = []

    total = len(records)
    lines.append(f"# {total} {header_title}")
    lines.append("")

    if not records:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    grouped: dict[str, list[tuple[int, JobRecord]]] = defaultdict(list)
    for index, record in enumerate(records):
        grouped[record.source].append((index, record))

    for source in sorted(grouped.keys()):
        jobs = grouped[source]
        lines.append(f"## {source} ({len(jobs)})")
        lines.append("")
        for num, (orig_index, job) in enumerate(jobs, start=1):
            lines.extend(_format_job(num, job))
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_job(num: int, job: JobRecord) -> list[str]:
    lines: list[str] = []
    lines.append(f"{num}. **{job.title}** @ {job.company}")

    bullets: list[str] = []
    if job.location:
        bullets.append(f"Location: {job.location}")

    salary = _format_salary(job)
    if salary:
        bullets.append(f"Salary: {salary}")

    posted = _format_posted_at(job)
    if posted:
        bullets.append(f"Posted: {posted}")

    url = job.apply_url or job.job_url
    if url:
        bullets.append(f"[Apply]({url})")

    for bullet in bullets:
        lines.append(f"   - {bullet}")

    return lines


def _format_salary(job: JobRecord) -> str:
    if job.salary_raw:
        return job.salary_raw
    if job.salary_min_usd is not None and job.salary_max_usd is not None:
        return f"${job.salary_min_usd:,}-${job.salary_max_usd:,}"
    if job.salary_min_usd is not None:
        return f"${job.salary_min_usd:,}+"
    if job.salary_max_usd is not None:
        return f"Up to ${job.salary_max_usd:,}"
    return ""


def _format_posted_at(job: JobRecord) -> str:
    if job.posted_at is None:
        return ""
    if isinstance(job.posted_at, datetime):
        return job.posted_at.isoformat()
    return str(job.posted_at)
