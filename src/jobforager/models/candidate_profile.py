from dataclasses import dataclass, field
from typing import Literal

_VALID_REMOTE_PREFERENCES = {
    "remote_only",
    "remote_preferred",
    "hybrid_ok",
    "any",
}


@dataclass(slots=True)
class CandidateProfile:
    """Canonical candidate preferences used for matching and ranking jobs."""

    target_titles: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    remote_preference: Literal[
        "remote_only", "remote_preferred", "hybrid_ok", "any"
    ] = "any"
    salary_floor_usd: int | None = None
    work_authorization: str | None = None
    resume_path: str | None = None
    source_toggles: dict[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.target_titles, list) or not all(
            isinstance(x, str) for x in self.target_titles
        ):
            raise ValueError("target_titles must be a list of strings.")
        if not isinstance(self.skills, list) or not all(
            isinstance(x, str) for x in self.skills
        ):
            raise ValueError("skills must be a list of strings.")
        if not isinstance(self.locations, list) or not all(
            isinstance(x, str) for x in self.locations
        ):
            raise ValueError("locations must be a list of strings.")
        if self.remote_preference not in _VALID_REMOTE_PREFERENCES:
            expected = ", ".join(sorted(_VALID_REMOTE_PREFERENCES))
            raise ValueError(f"remote_preference must be one of: {expected}.")
        if self.salary_floor_usd is not None and self.salary_floor_usd < 0:
            raise ValueError("salary_floor_usd must be non-negative.")
        if not isinstance(self.source_toggles, dict) or not all(
            isinstance(k, str) and isinstance(v, bool)
            for k, v in self.source_toggles.items()
        ):
            raise ValueError(
                "source_toggles must be a dict with string keys and boolean values."
            )
