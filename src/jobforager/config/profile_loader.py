from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any

from jobforager.models import CandidateProfile
from jobforager.models.candidate_profile import _VALID_REMOTE_PREFERENCES

_REMOTE_PREFERENCE_ALIASES = {
    "remoteonly": "remote_only",
    "remotepreferred": "remote_preferred",
}


def load_candidate_profile(path: str | Path) -> CandidateProfile:
    """Load CandidateProfile from a profile TOML file."""

    profile_path = Path(path)
    with profile_path.open("rb") as handle:
        data = tomllib.load(handle)

    profile_section = _as_section(data, "profile")
    targets_section = _as_section(data, "targets")
    preferences_section = _as_section(data, "preferences")

    return CandidateProfile(
        target_titles=_coerce_string_list(targets_section.get("titles"), "targets.titles"),
        skills=_coerce_string_list(targets_section.get("skills"), "targets.skills"),
        locations=_load_locations(profile_section, targets_section),
        remote_preference=_normalize_remote_preference(preferences_section),
        salary_floor_usd=_coerce_optional_int(
            preferences_section.get(
                "salary_floor_usd", preferences_section.get("minbasesalary_usd")
            ),
            "preferences.salary_floor_usd",
            min_value=0,
        ),
        work_authorization=_coerce_optional_string(
            profile_section.get(
                "work_authorization", profile_section.get("workauthorization")
            ),
            "profile.work_authorization",
        ),
        resume_path=_coerce_optional_string(
            profile_section.get("resume_path", profile_section.get("resumepath")),
            "profile.resume_path",
        ),
        source_toggles=_load_source_toggles(data),
    )


def _load_source_toggles(data: dict[str, Any]) -> dict[str, bool]:
    sources_section = _as_section(data, "sources")
    toggles: dict[str, bool] = {}
    for key, value in sources_section.items():
        if isinstance(key, str) and key.startswith("enable_"):
            source_name = key[len("enable_"):]
            if isinstance(value, bool):
                toggles[source_name] = value
            elif isinstance(value, str):
                toggles[source_name] = value.strip().lower() in ("true", "1", "yes")
    return toggles


def _as_section(data: dict[str, Any], section_name: str) -> dict[str, Any]:
    section = data.get(section_name, {})
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ValueError(f"Expected [{section_name}] section to be a TOML table.")
    return section


def _load_locations(
    profile_section: dict[str, Any], targets_section: dict[str, Any]
) -> list[str]:
    if "locations" in targets_section:
        return _coerce_string_list(targets_section.get("locations"), "targets.locations")

    profile_location = _coerce_optional_string(
        profile_section.get("location"), "profile.location"
    )
    return [profile_location] if profile_location else []


def _normalize_remote_preference(preferences_section: dict[str, Any]) -> str:
    raw_value = preferences_section.get(
        "remote_preference", preferences_section.get("remotepreference", "any")
    )

    if raw_value is None:
        return "any"
    if not isinstance(raw_value, str):
        raise ValueError("Invalid remote_preference value: expected a string.")

    normalized = _REMOTE_PREFERENCE_ALIASES.get(raw_value.strip().lower(), raw_value)
    normalized = normalized.strip().lower()
    if normalized not in _VALID_REMOTE_PREFERENCES:
        expected = ", ".join(sorted(_VALID_REMOTE_PREFERENCES))
        raise ValueError(
            f"Invalid remote_preference value '{raw_value}'. Expected one of: {expected}."
        )
    return normalized


def _coerce_string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Expected {field_name} to be a list of strings.")

    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(
                f"Expected {field_name}[{index}] to be a string, got {type(item).__name__}."
            )
        normalized = item.strip()
        if normalized:
            items.append(normalized)
    return items


def _coerce_optional_int(
    value: Any, field_name: str, min_value: int | None = None
) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"Expected {field_name} to be an integer.")
    if isinstance(value, int):
        if min_value is not None and value < min_value:
            raise ValueError(f"Expected {field_name} to be at least {min_value}.")
        return value
    if isinstance(value, str):
        normalized = value.strip().replace(",", "")
        if not normalized:
            return None
        try:
            parsed = int(normalized)
        except ValueError as exc:
            raise ValueError(f"Expected {field_name} to be an integer.") from exc
        if min_value is not None and parsed < min_value:
            raise ValueError(f"Expected {field_name} to be at least {min_value}.")
        return parsed
    raise ValueError(f"Expected {field_name} to be an integer.")


def _coerce_optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Expected {field_name} to be a string.")

    normalized = value.strip()
    return normalized or None
