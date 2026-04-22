from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

_VALID_REMOTE_TYPES = {"remote", "hybrid", "onsite", "unknown"}


@dataclass(slots=True)
class JobRecord:
    """Canonical normalized job record from any source."""

    source: str
    title: str
    company: str
    job_url: str

    location: str | None = None
    remote_type: Literal["remote", "hybrid", "onsite", "unknown"] | None = None

    salary_raw: str | None = None
    salary_min_usd: int | None = None
    salary_max_usd: int | None = None

    posted_at: datetime | None = None
    apply_url: str | None = None

    ats_platform: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)

    external_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must be a non-empty string.")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("title must be a non-empty string.")
        if not isinstance(self.company, str) or not self.company.strip():
            raise ValueError("company must be a non-empty string.")
        if not isinstance(self.job_url, str) or not self.job_url.strip():
            raise ValueError("job_url must be a non-empty string.")
        if self.remote_type is not None and self.remote_type not in _VALID_REMOTE_TYPES:
            expected = ", ".join(sorted(_VALID_REMOTE_TYPES))
            raise ValueError(f"remote_type must be one of: {expected}.")
        if self.salary_min_usd is not None and self.salary_min_usd < 0:
            raise ValueError("salary_min_usd must be non-negative.")
        if self.salary_max_usd is not None and self.salary_max_usd < 0:
            raise ValueError("salary_max_usd must be non-negative.")
        if not isinstance(self.tags, list) or not all(
            isinstance(x, str) for x in self.tags
        ):
            raise ValueError("tags must be a list of strings.")
