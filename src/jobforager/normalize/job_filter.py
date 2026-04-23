from __future__ import annotations

from jobforager.models import CandidateProfile, JobRecord
from jobforager.normalize.location_resolver import location_matches


def filter_jobs(
    records: list[JobRecord], profile: CandidateProfile
) -> list[JobRecord]:
    result: list[JobRecord] = []
    for job in records:
        if not _matches_remote_preference(job, profile):
            continue
        if not _matches_locations(job, profile):
            continue
        if not _matches_titles(job, profile):
            continue
        if not _matches_skills(job, profile):
            continue
        if not _matches_salary(job, profile):
            continue
        result.append(job)
    return result


def _matches_remote_preference(job: JobRecord, profile: CandidateProfile) -> bool:
    preference = profile.remote_preference
    job_remote = job.remote_type

    if preference == "any":
        return True
    if preference == "remote_only":
        return job_remote == "remote"
    if preference == "remote_preferred":
        return job_remote in ("remote", "hybrid", "unknown", None)
    if preference == "hybrid_ok":
        return job_remote in ("remote", "hybrid", "onsite", "unknown", None)
    return True


def _matches_locations(job: JobRecord, profile: CandidateProfile) -> bool:
    if not profile.locations:
        return True
    return location_matches(job.location, profile.locations)


def _matches_titles(job: JobRecord, profile: CandidateProfile) -> bool:
    if not profile.target_titles:
        return True
    job_title = job.title.lower()
    return any(t.lower() in job_title or job_title in t.lower() for t in profile.target_titles)


def _matches_skills(job: JobRecord, profile: CandidateProfile) -> bool:
    if not profile.skills:
        return True
    if not job.tags:
        return True
    profile_skills = {s.lower() for s in profile.skills}
    job_tags = {t.lower() for t in job.tags}
    return not profile_skills.isdisjoint(job_tags)


def _matches_salary(job: JobRecord, profile: CandidateProfile) -> bool:
    if profile.salary_floor_usd is None:
        return True
    if job.salary_max_usd is None:
        return True
    return job.salary_max_usd >= profile.salary_floor_usd
