# CLI Reference

## Command Overview

```bash
job-forager <command> [options]
```

| Command | Description |
|---------|-------------|
| `help` | Show scaffold status and available commands |
| `hunt` | Run ingestion foundation checks (Phase 1.2 dry-run) |
| `search` | Search live job sources with filtering and export |
| `validate` | Validate a candidate profile TOML file |

## `help`

Show current project status.

```bash
python -m jobforager.cli help
```

Output:
```
job-forager Phase 1.2 ingestion foundation is ready.
Dry-run config/normalize/dedupe flow is available.
No real collectors/ATS/scoring/apply logic implemented yet.
```

## `hunt` — Dry-Run Ingestion

Simulates the full pipeline using sample data or a provided records file. Useful for testing profile configuration and export formats.

```bash
python -m jobforager.cli hunt --dry-run \
  --profile config/profile.example.toml \
  --output-json results.json \
  --output-csv results.csv
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | (required) | Run the demo flow with sample data |
| `--profile` | `config/profile.example.toml` | Path to TOML profile |
| `--records` | (built-in sample) | Path to JSON/JSONL/CSV file with raw records |
| `--output-json` | (none) | Write normalized results to JSON file |
| `--output-csv` | (none) | Write normalized results to CSV file |

### Example Output

```
job-forager dry run
profile=config/profile.example.toml
profile_summary titles=1 skills=2 locations=0 remote_preference=remote_only
sources_enabled=sample records=1 unique_keys=1 duplicates=0
1. Senior Software Engineer @ Example Labs [remotive]
   dedupe_key=remotive|...|Senior Software Engineer|Example Labs
---
summary total_records=1
summary unique=1 duplicates=0
summary sources=sample
status=completed_clean
```

## `search` — Live Job Search

The primary command. Fetches live jobs from enabled sources, normalizes, filters, deduplicates, validates URLs, and optionally exports.

```bash
python -m jobforager.cli search \
  --sources remotive,hackernews,greenhouse,lever,hiringcafe \
  --keywords "python,senior" \
  --exclude "staffing,agency" \
  --location "remote" \
  --level senior \
  --hide-recruiters \
  --last 7d \
  --profile config/profile.example.toml \
  --output-json results.json
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--sources` | `remotive,hackernews` | Comma-separated source list. Available: `remotive`, `hackernews`, `remoteok`, `arbeitnow`, `greenhouse`, `lever`, `ashby`, `workday`, `smartrecruiters`, `hiringcafe`, `linkedin`, `indeed`, `glassdoor` |
| `--keywords` | (none) | Comma-separated keywords to match in title, company, tags, or description |
| `--exclude` | (none) | Comma-separated keywords to EXCLUDE from results |
| `--location` | (none) | Free-text location filter (substring match) |
| `--level` | (none) | Filter by experience level: `intern`, `entry`, `mid`, `senior` |
| `--hide-recruiters` | (none) | Hide jobs from staffing agencies and recruiting firms |
| `--since` | (none) | Only show jobs posted on or after this date (`YYYY-MM-DD`) |
| `--last` | (none) | Duration window: `24h`, `7d`, `30d` |
| `--workers` | `30` | Concurrent threads for multi-endpoint sources |
| `--profile` | (none) | Path to profile TOML for additional filtering |
| `--output-json` | (none) | Path to write normalized records as JSON |
| `--output-csv` | (none) | Path to write normalized records as CSV |

### Source-Specific Notes

- **`greenhouse`**: **8,032 boards**, all jobs per board, concurrent fetching. Fastest ATS source.
- **`lever`**: **4,368 companies**, all jobs per company, concurrent fetching.
- **`ashby`**: **2,796 boards**, all jobs per board, concurrent fetching.
- **`workday`**: All companies from live list, 20 jobs per page, **all pages fetched** up to 2,000 per company (API hard limit). Slowest source.
- **`smartrecruiters`**: All slugs from live list, 100 jobs per page, **all pages fetched**.
- **`hiringcafe`**: 2.1M+ job index, 1,000 jobs per page, **all pages fetched**. Falls back through urllib → curl_cffi → Playwright for Cloudflare bypass.
- **`remotive`, `remoteok`, `arbeitnow`**: Single API call, all jobs returned.
- **`hackernews`**: Top 50 comments from current month's thread.
- **`linkedin`, `indeed`, `glassdoor`**: Scraped via **JobSpy** (optional dependency). Install with `pip install python-jobspy`. Results capped at 50 per site by default (last 7 days). `--keywords` and `--title-keywords` are forwarded to the scraper as the search term.

### Example: Search All Sources

```bash
python -m jobforager.cli search \
  --sources all \
  --keywords "python" \
  --last 7d \
  --output-json all_sources.json
```

### Example: Search JobSpy Sources (LinkedIn + Indeed + Glassdoor)

```bash
pip install python-jobspy
python -m jobforager.cli search \
  --sources linkedin,indeed,glassdoor \
  --keywords "software engineer" \
  --location "London,UK" \
  --output-json jobspy_results.json
```

### Example: Search ATS Platforms Only

```bash
python -m jobforager.cli search \
  --sources greenhouse,lever,ashby \
  --keywords "senior,staff" \
  --location "remote" \
  --profile config/profile.example.toml
```

### Example: Quick Remote Jobs

```bash
python -m jobforager.cli search \
  --sources remotive,remoteok,arbeitnow \
  --location "remote" \
  --last 24h
```

### Example Output

```
job-forager search
sources_queried=greenhouse,lever
fetched=156
matched=12
validated=11
invalid=1
unique=12

1. Senior Backend Engineer @ Stripe [greenhouse]
   url=https://boards.greenhouse.io/stripe/jobs/12345
   location=Remote, US
   posted_at=2024-01-15T09:00:00-05:00
   validated=ok

2. Staff Software Engineer @ Netflix [lever]
   url=https://jobs.lever.co/netflix/abc-123
   location=Los Gatos, CA
   posted_at=2024-01-14T10:30:00Z
   validated=ok

---
summary total_records=12
summary unique=12 duplicates=0
summary sources=greenhouse,lever
summary validated=11 invalid=1
summary by_source greenhouse=7 lever=5
status=completed_clean
```

## `validate` — Profile Validation

Validate a candidate profile TOML file without running a search.

```bash
python -m jobforager.cli validate --profile config/profile.example.toml
```

Output:
```
job-forager validate
profile=config/profile.example.toml
profile_status=ok
profile_summary titles=1 skills=2 locations=0 remote_preference=remote_only
sources_enabled=remotive,arbeitnow,remoteok
filters_active=titles,skills,remote_preference
```

### Validation Checks

- Required sections: `[profile]`, `[targets]`, `[preferences]`, `[sources]`
- `remote_preference` must be one of: `remote_only`, `remote_preferred`, `hybrid_ok`, `any`
- `minbasesalary_usd` must be non-negative
- Source toggles must be boolean values
- Unknown sections/keys are ignored

## Environment Setup

### Linux / macOS

```bash
export PYTHONPATH=src
python -m jobforager.cli help
```

### Windows (PowerShell)

```powershell
$env:PYTHONPATH="src"
python -m jobforager.cli help
```

### Windows (CMD)

```cmd
set PYTHONPATH=src
python -m jobforager.cli help
```

### Installed Package

If installed via `pip install -e .`:

```bash
job-forager help
job-forager search --sources greenhouse,lever --keywords python
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'jobforager'`

Set `PYTHONPATH=src` before running, or install the package with `pip install -e .`.

### No jobs returned

- Check your network connection
- Some APIs may block requests without proper headers (collectors include `User-Agent`)
- Try a broader search (fewer keywords, no location filter)
- Use `python -m jobforager.cli search --sources remotive` to test a single source

### Workday search is very slow

Workday requires fetching a CSRF token per company, then making paginated POST requests. Consider:
- Using `--max_results_per_company` if calling programmatically
- Using other sources for bulk discovery, Workday only for specific companies

### SSL certificate errors

Collectors use `ssl.create_default_context()` with `check_hostname=False` and `verify_mode=ssl.CERT_NONE` to handle varied certificate configurations. This is intentional for broad compatibility.
