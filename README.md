<div align="center">
  <img src="assets/logo.svg" alt="Job Forager Logo" width="120" height="120">
  <h1>Job Forager</h1>
  <p><strong>The best free, open-source job hunting automation tool.</strong></p>
  <p>Discover real jobs from thousands of companies across every major ATS platform and job board — no paid APIs required.</p>

  <p>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
    <img src="https://img.shields.io/badge/Sources-17-green.svg" alt="17 Sources">
    <img src="https://img.shields.io/badge/Tests-322-brightgreen.svg" alt="322 Tests">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  </p>
</div>

---

## What This Project Does

Job Forager is a Python CLI tool that aggregates live job listings from **17 different sources** covering thousands of companies. It normalizes, deduplicates, filters, and ranks jobs against your candidate profile — giving you a curated list of real opportunities with direct apply links.

### Why Job Forager?

- **No paywalls** — Every source is free. No API keys required for 15 of 17 sources.
- **No browser automation** — Pure HTTP/API requests. Runs in 2 seconds on CI, not 2 minutes with Selenium.
- **No stale data** — Every run hits live APIs. No job-level cache pretending yesterday's postings are fresh.
- **Set it and forget it** — One GitHub Actions workflow, scheduled daily. New jobs land in your artifacts automatically.
- **Zero dependencies** — Core runs on Python stdlib only. No pip install hell.

### Key Capabilities

- **Multi-source job discovery** — Fetch live jobs from Remotive, Hacker News, RemoteOK, ArbeitNow, Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Hiring.cafe, WeWorkRemotely, Adzuna, Pinpoint, Two Sigma, LinkedIn, Indeed, and Glassdoor
- **Maximum coverage, no limits** — Every company endpoint and every pagination page is fetched. Greenhouse: 8,032 boards. Lever: 4,368 companies. Ashby: 2,796 boards. SmartRecruiters: 812 companies. Workday: 2,836 companies. All concurrently.
- **Concurrent fetching** — ThreadPoolExecutor with configurable workers (`--workers 30`). 100 boards in ~2 seconds.
- **Company list expansion** — Automatically discovers thousands of companies from public GitHub repositories (Feashliaa, stapply-ai). Fresh data on every run, no caching.
- **ATS auto-detection** — Identifies which Applicant Tracking System each job uses from URL patterns
- **Normalization & deduplication** — Converts disparate API formats into a single canonical `JobRecord` format, removes duplicates
- **Profile-based filtering** — Filter by job title, skills, location, remote preference, salary floor, and date
- **Advanced CLI filters** — `--exclude`, `--level` (intern/entry/mid/senior), `--hide-recruiters`
- **URL validation** — Checks job URLs for 404s and availability
- **Export** — Output results as JSON, CSV, or Markdown
- **One dependency for scraping** — `python-jobspy` is required for LinkedIn, Indeed, and Glassdoor. All other 14 sources use Python stdlib only (`urllib`, `dataclasses`, `argparse`, `sqlite3`, etc.).
- **Incremental discovery** — SQLite-backed job tracking. Run once to build the database, then use `--since-last-run` to output only jobs discovered since the previous execution. Perfect for scheduled CI runs.
- **CI-optimized** — Designed for GitHub Actions with built-in caching support. No Docker, no server, no hosting required.

---

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/nipunsomani/job-forager.git
cd job-forager

# Ensure Python 3.10+ is available
python --version  # >= 3.10

# Optional: install as editable package
pip install -e .
```

### Verify Installation

```bash
# If installed with pip install -e .
job-forager help

# Or run directly with PYTHONPATH
export PYTHONPATH=src  # Linux/Mac
# $env:PYTHONPATH="src"  # PowerShell
python -m jobforager.cli help
```

---

## Quick Start

### 1. Create Your Profile

Copy the example profile and customize it:

```bash
cp config/profile.example.toml config/profile.toml
```

Edit `config/profile.toml` with your details. See [`config/profile.example.toml`](config/profile.example.toml) for the full template.

### 2. Search for Jobs

```bash
# Search all default sources with your profile
python -m jobforager.cli search --profile config/profile.toml

# Search specific sources with keywords and export
python -m jobforager.cli search \
  --sources remotive,greenhouse,lever \
  --keywords "python,senior" \
  --location "remote" \
  --last 7d \
  --output-json results.json
```

See [`docs/CLI_REFERENCE.md`](docs/CLI_REFERENCE.md) for all commands, flags, and examples.

### 3. Validate Your Profile

```bash
python -m jobforager.cli validate --profile config/profile.toml
```

### 4. Run a Dry-Run Ingestion Demo

```bash
python -m jobforager.cli hunt --dry-run --profile config/profile.toml
```

---

## Usage

See [`docs/CLI_REFERENCE.md`](docs/CLI_REFERENCE.md) for all commands, flags, and examples.

## Source Coverage

| Source | Type | Coverage | Auth |
|--------|------|----------|------|
| **Remotive** | API | Remote jobs board | — |
| **Hacker News** | API | Monthly "Who is hiring?" thread | — |
| **RemoteOK** | API | Remote jobs board | — |
| **ArbeitNow** | API | EU remote jobs | — |
| **Greenhouse** | API | 8,032+ company boards | — |
| **Lever** | API | 4,368+ companies | — |
| **Ashby** | API | 2,796+ boards | — |
| **SmartRecruiters** | API | 812+ companies | — |
| **Workday** | API | 2,836+ companies | — |
| **Hiring.cafe** | Next.js API | Aggregator (200K+ jobs) | — |
| **WeWorkRemotely** | RSS | Remote jobs board | — |
| **Adzuna** | API | Global aggregator | Free key |
| **Pinpoint** | API | 76+ subdomains | — |
| **Two Sigma** | RSS (Avature) | Quant finance roles | — |
| **LinkedIn** | Scraping | Aggregator | `python-jobspy` |
| **Indeed** | Scraping | Aggregator | `python-jobspy` |
| **Glassdoor** | Scraping | Aggregator | `python-jobspy`* |

\* Glassdoor is currently broken upstream in `python-jobspy`.

## Configuration

Job Forager uses a TOML profile for personalized filtering. The profile is applied **before** CLI flags, so CLI flags further narrow the results.

When you provide a profile, jobs are filtered with **AND** logic across:
- **Remote preference** — `remote_only` excludes non-remote jobs; `remote_preferred` allows hybrid; `any` allows all
- **Location** — substring match against your specified locations
- **Title** — substring match against your target titles
- **Skills** — job must mention at least one of your skills in title, tags, or description
- **Salary floor** — jobs below your minimum are excluded

See [`config/profile.example.toml`](config/profile.example.toml) for the complete template.

---

## Docs

- [`docs/CLI_REFERENCE.md`](docs/CLI_REFERENCE.md) — Commands, flags, and examples
- [`docs/API_SOURCES.md`](docs/API_SOURCES.md) — Supported job sources and coverage

---

## Development

```bash
# Compile check
python -m compileall src

# Run tests
PYTHONPATH=src python -m unittest discover -s tests -v
```

---

## Scheduled Job Searches with GitHub Actions

You can run Job Forager on a schedule using GitHub Actions. A workflow file is included in `.github/workflows/daily-job-search.yml`.

### Setup

1. Fork this repository
2. Enable GitHub Actions in your fork ( Actions tab → "I understand my workflows, go ahead and enable them")
3. The workflow runs daily at 01:00 UTC and can also be triggered manually

### How Incremental Search Works in CI

The workflow uses `actions/cache` to persist the job database between runs:

```
Day 1: No cache → fetches all jobs → saves DB to cache
Day 2: Restores DB → fetches jobs → outputs only new ones → updates cache
```

This means your daily artifact (`new_jobs.json`) contains only jobs discovered since yesterday, not the entire internet.

### Workflow Features

- Runs on Ubuntu latest with Python 3.12
- Restores job database from cache between runs (incremental discovery)
- Supports JSON output upload as artifact
- Configurable schedule via cron expression
- No profile required — keywords and filters are inline in the workflow

### Manual Trigger

```bash
# Trigger from GitHub CLI
gh workflow run daily-job-search
```

---

## Credits

- Company lists sourced from [Feashliaa/job-board-aggregator](https://github.com/Feashliaa/job-board-aggregator) and [stapply-ai/ats-scrapers](https://github.com/stapply-ai/ats-scrapers)
- Workday reverse-engineering based on [stapply-ai/ats-scrapers](https://github.com/stapply-ai/ats-scrapers)
