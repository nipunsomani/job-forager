# Architecture

## Overview

Job Forager uses a layered architecture designed for extensibility, testability, and zero external dependencies. Every component is a pure Python standard library module.

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                             │
│              cli/ - argparse entry point                     │
│         Commands: hunt, search, validate, help               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Collector Layer                           │
│   CollectorRegistry - orchestrates N source collectors       │
│   Sources: remotive, hackernews, remoteok, arbeitnow,        │
│            greenhouse, lever, ashby, workday,                │
│            smartrecruiters, hiringcafe                       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Normalization Layer                        │
│   normalize_raw_job_record() → JobRecord (canonical)         │
│   build_dedupe_key() - composite key for deduplication       │
│   filter_jobs() - profile-based filtering                    │
│   apply_search_filters() - keyword/location/date             │
│   detect_ats_platform() - URL pattern matching               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Model Layer                              │
│   JobRecord - canonical dataclass (slots, validated)         │
│   CandidateProfile - TOML-loaded preferences                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                      │
│   company_lists.py - fetch public company lists live         │
│   config/profile_loader.py - TOML parsing & validation       │
│   exporters/ - JSON/CSV writers                              │
│   collectors/registry.py - source registration & execution   │
└─────────────────────────────────────────────────────────────┘
```

## Module Reference

### `cli/`
Entry point package. Parses arguments, dispatches to `hunt`, `search`, `validate`, or `help` subcommands. Orchestrates the full pipeline: collect → normalize → filter → dedupe → validate → export.

### `search/` - Collectors
Each module fetches jobs from one external source and returns `list[dict[str, Any]]`.

| Module | Source | Auth | Pagination | Special Notes |
|--------|--------|------|------------|---------------|
| `remotive.py` | Remotive API | No | Single page | Requires `Referer` header |
| `hackernews.py` | HN "Who is Hiring" | No | Algolia search + Firebase | Thread detection via Algolia |
| `remoteok.py` | RemoteOK API | No | Single page | Skips metadata records |
| `arbeitnow.py` | ArbeitNow API | No | Single page | Response wrapped in `{"data": [...]}` |
| `greenhouse.py` | Greenhouse Job Board API | No | Per-board | `boards-api.greenhouse.io/v1/boards/{token}/jobs` |
| `lever.py` | Lever Postings API | No | Per-company | `api.lever.co/v0/postings/{company}?mode=json` |
| `ashby.py` | Ashby Posting API | No | Per-board | `api.ashbyhq.com/posting-api/job-board/{name}` |
| `workday.py` | Workday Calypso API (reverse-engineered) | No | POST pagination | Requires CSRF token from career page |
| `smartrecruiters.py` | SmartRecruiters Public API | No | GET offset/limit | Constructs URLs from slug+id |
| `hiringcafe.py` | Hiring.cafe Aggregated API | No | POST pagination (1000/page) | Queries 2.1M+ job index |

### `models/` - Canonical Data
- `JobRecord` - Immutable dataclass with `__post_init__` validation. Fields: `source`, `title`, `company`, `job_url`, `location`, `remote_type`, `salary_raw`, `salary_min_usd`, `salary_max_usd`, `posted_at`, `apply_url`, `ats_platform`, `description`, `tags`, `external_id`, `metadata`.
- `CandidateProfile` - Loaded from TOML. Fields: `target_titles`, `skills`, `locations`, `remote_preference`, `salary_floor_usd`, `source_toggles`.

### `normalize/` - Processing Pipeline
- `job_normalizer.py` - `normalize_raw_job_record()` maps raw dicts → `JobRecord`. Handles type coercion, remote type aliases, tag normalization, ISO date parsing.
- `dedupe.py` - `build_dedupe_key()` creates a deterministic hash from `(source, external_id, title, company)`.
- `job_filter.py` - `filter_jobs()` applies profile-based filters (titles, skills, locations, remote, salary).
- `ats_detector.py` - `detect_ats_platform()` matches URL substrings to ATS platforms. `detect_ats_from_record()` checks `job_url`, `apply_url`, and `source` fields.

### `config/` - Configuration
- `profile_loader.py` - Parses TOML into `CandidateProfile`. Validates enums, non-negative salaries, source toggles.

### `company_lists.py` - Company Discovery
Fetches public company lists live from GitHub on every run. No local caching.
- Feashliaa/job-board-aggregator: Greenhouse, Lever, Ashby (JSON arrays)
- stapply-ai/ats-scrapers: SmartRecruiters, Workday (CSV files)
- Falls back to curated hardcoded defaults if network is unavailable

### `collectors/` - Registry
- `registry.py` - `CollectorRegistry` registers callables by name. `collect()` runs enabled sources in sequence, isolating failures per source.
- `file_adapter.py` - Loads raw records from JSON, JSONL, or CSV files.

### `exporters/` - Output
- `normalized_json.py` - Writes `list[JobRecord]` + dedupe keys to JSON.
- `normalized_csv.py` - Writes `list[JobRecord]` + dedupe keys to CSV.

## Data Flow (Detailed)

### 1. Collection
```python
registry = CollectorRegistry()
registry.register("remotive", collect_remotive_jobs)
registry.register("greenhouse", collect_greenhouse_jobs)
# ... etc

enabled = {"remotive": True, "greenhouse": True}
raw_records = registry.collect(enabled, errors={})
# → list[dict] from all enabled sources
```

### 2. Normalization
```python
for record in raw_records:
    job = normalize_raw_job_record(record)
    # → JobRecord with validated fields + auto-detected ATS platform
```

### 3. Filtering
```python
filtered = filter_jobs(normalized, profile)        # profile-based
filtered = apply_search_filters(                   # CLI search-based
    filtered,
    keywords=["python"],
    location_query="remote",
    since=datetime(...),
    last_duration=timedelta(days=7),
)
```

### 4. Deduplication
```python
dedupe_keys = [build_dedupe_key(job) for job in filtered]
unique = dedupe_by_key_and_url(filtered, dedupe_keys)
```

### 5. Validation
```python
results = validate_job_urls(unique)
# → HEAD request each URL, report 200/404/timeout
```

### 6. Export
```python
write_normalized_json(unique, keys, "results.json")
write_normalized_csv(unique, keys, "results.csv")
```

## Design Decisions

### Standard Library Only
No `requests`, `aiohttp`, `pydantic`, `click`, or `tomli`. Everything uses `urllib.request`, `dataclasses`, `argparse`, and `tomllib` (Python 3.11+) with a fallback.

### Pure Functions for Normalization
`normalize_raw_job_record()`, `build_dedupe_key()`, and `filter_jobs()` are pure functions with no side effects. Easy to test, compose, and reason about.

### Graceful Degradation
Every collector wraps its HTTP call in `try/except` and returns `[]` on failure. The registry isolates failures per source - one broken API doesn't crash the whole search.

### Live Fetching
Company lists are fetched live from GitHub on every run. If the network is unavailable, fallback to curated default lists hardcoded in `company_lists.py`.

## Phase Boundaries

Current approved phase: **Phase 1.x - Ingestion Foundation**

Safe to implement:
- New collectors (within Phase 1.x)
- CLI improvements
- Normalization utilities
- Tests and docs

Explicitly out of scope:
- ATS automation / browser automation
- Job submission
- Scoring/ranking engine (Phase 3)
- Database persistence
- Live external integrations beyond job fetching

See `AGENTS.md` for full phase rules.
