# AGENTS.md — Job Forager

Python 3.10+ CLI that aggregates live job listings from 14 sources. Zero core dependencies (stdlib only).

## Project Tenets

1. **Best lightweight job discovery engine** — Maximum sources, maximum reliability, zero dependencies, perfect for CI and scripting.
2. **CLI-first** — No web UI, no dashboards, no servers. Terminal output and file exports (JSON/CSV) only.
3. **Built for CI** — Designed to run in GitHub Actions, cron jobs, and headless environments without Docker, without hosting, and without managing a server. Configure once, schedule it, get jobs in your inbox or artifacts.
4. **Due diligence over surface answers** — Before implementing or recommending anything, research the underlying mechanism (read source code, test APIs, verify behavior). Never assume. Always verify with actual data.

## Run the project

```bash
# Preferred: run without installing
PYTHONPATH=src python -m jobforager.cli help

# Or install as editable package
pip install -e .
job-forager help
```

## Tests

```bash
# Must set PYTHONPATH; tests use unittest, not pytest
PYTHONPATH=src python -m unittest discover -s tests -v

# Run a single test module
PYTHONPATH=src python -m unittest tests.test_search_remotive -v
```

## CI verification order

1. `python -m compileall src`
2. `PYTHONPATH=src python -m jobforager.cli help` (smoke test)
3. `PYTHONPATH=src python -m unittest discover -s tests -v`

## Architecture

- `src/jobforager/cli/` — Entrypoint (`__main__.py`), parser, commands, pipeline orchestration.
- `src/jobforager/search/` — One module per live source (remotive, greenhouse, lever, ashby, workday, smartrecruiters, hackernews, remoteok, arbeitnow, hiringcafe, adzuna, jobspy_source).
- `src/jobforager/normalize/` — Normalization, deduplication, filtering, ATS detection, experience-level extraction, recruiter detection.
- `src/jobforager/models/` — `JobRecord` and `CandidateProfile` dataclasses.
- `src/jobforager/collectors/` — `CollectorRegistry` (sequential + `ThreadPoolExecutor` concurrent collection).
- `src/jobforager/exporters/` — JSON and CSV writers.
- `src/jobforager/config/` — TOML profile loader.
- `src/jobforager/storage/` — SQLite-backed `JobStore` for incremental discovery and job persistence across runs.

## Key conventions

- Use `from __future__ import annotations` in every module.
- The CLI package is `jobforager.cli`; console script entrypoint is `job-forager`.
- No external runtime dependencies. Optional: `playwright` for CI scraping; `python-jobspy` for LinkedIn/Indeed/Glassdoor sources.

## Commands and gotchas

- `hunt` only supports `--dry-run` (Phase 1.2 scaffolding).
- `search` hits live APIs. Default sources: `remotive,hackernews`. Use `--sources all` for all 14.
- `search --workers 30` is the default concurrency level for multi-company sources.
- `search --since-last-run` outputs only jobs discovered since the previous run (uses SQLite DB at `~/.cache/jobforager/jobs.db` or custom `--db-path`).
- Workday is slow; profile example disables it by default (`enable_workday = false`).
- Company lists are fetched dynamically from public GitHub repos on every run (no local cache).
- Profile path defaults to `config/profile.example.toml` for `hunt`/`validate`; `search` has no default profile.
- Optional JobSpy sources (`linkedin`, `indeed`, `glassdoor`) require `pip install python-jobspy`.
- Adzuna requires a free developer API key (`ADZUNA_APP_ID` + `ADZUNA_APP_KEY`). Sign up at `developer.adzuna.com`. If keys are not set, the source silently skips.
- Default DB location: `~/.cache/jobforager/jobs.db` (Linux/macOS) or `%LOCALAPPDATA%\jobforager\jobs.db` (Windows).

## Known limitations

### Hiring.cafe on CI runners
Hiring.cafe is protected by Cloudflare. GitHub Actions runners use Azure/datacenter IPs that are blocked at the network edge (IP/reputation-level block). In CI, `hiringcafe` returns empty results. This is expected and acceptable — Hiring.cafe mostly aggregates jobs from ATSs we already hit directly (Greenhouse, Lever, Ashby, Workday, SmartRecruiters). The current fallback chain (`urllib` → `curl_cffi` → `Playwright`) does not bypass this in CI. See deep-dive notes in repo history for details.

**To revisit later:** Evaluate whether to simplify `hiringcafe.py` by dropping `curl_cffi` and `Playwright` fallbacks (dead weight for CI) or keep them for local users on residential IPs.

### startup.jobs — evaluated and rejected
`startup.jobs` was evaluated as a potential source (job-ops supports it). It uses Algolia for search, but the Algolia API key is **referrer-restricted** and the site itself is protected by Cloudflare. Direct HTTP and even `curl_cffi` can fetch the HTML page, but the extracted Algolia credentials fail when used outside the browser context. Job-ops solves this with Camoufox (stealth browser) + `page.evaluate()` to call Algolia from inside the page. We intentionally do not adopt browser-heavy dependencies (violates "zero core dependencies" and "CI-optimized" tenets). Rejected as unimplementable within our architecture.

## GitHub Actions

- `.github/workflows/ci.yml` — runs on push/PR to `main`, matrix Python 3.10–3.13.
- `.github/workflows/daily-job-search.yml` — scheduled at 01:00 UTC. Uses `actions/cache` to persist the job database between runs for incremental discovery. Outputs only new jobs via `--since-last-run`.
