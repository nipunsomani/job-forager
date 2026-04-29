# Roadmap

This document outlines planned improvements and extensions for Job Forager. Items are organized by phase and priority.

## Phase 1.x - Ingestion Foundation (Current)

### High Priority

- [ ] **More job sources**
  - LinkedIn (requires browser automation or third-party API - research needed)
  - Indeed (RSS feeds or scraping)
  - ZipRecruiter (API or scraping)
  - We Work Remotely (scraping)
  - AngelList / Wellfound (API)
  - Glassdoor (API or scraping)
  - GitHub Jobs (if revived)

- [ ] **Improved company list discovery**
  - Parse Crunchbase for startup job boards
  - Extract from Y Combinator company directory
  - Sitemap-based discovery (parse `sitemap.xml` for `/careers` pages)
  - Community-contributed company lists via PRs

- [ ] **Better rate limiting**
  - Exponential backoff with jitter
  - Per-source rate limit configuration
  - Concurrent fetching with `threading` (respecting rate limits)

- [ ] **Result caching (optional)**
  - Cache raw API responses for 1-6 hours (not company lists - those are always fetched live)
  - Cache normalized records to avoid re-processing
  - SQLite or JSON-based cache store

### Medium Priority

- [ ] **Enhanced filtering**
  - Exclude keywords (negative filters)
  - Regex-based title matching
  - Company size filtering (if data available)
  - Industry filtering

- [ ] **Output improvements**
  - HTML report generation
  - Markdown table output
  - Email-friendly formatted output
  - Integration with Google Sheets API

- [ ] **Configuration improvements**
  - Environment variable overrides
  - Multiple profile support
  - Profile inheritance/composition
  - CLI wizard for first-time setup

## Phase 2 - ATS Detection & Apply Routing

### High Priority

- [ ] **ATS-specific apply link extraction**
  - Greenhouse: direct apply URL construction
  - Lever: `applyUrl` field already present
  - Ashby: `applyUrl` field already present
  - Workday: extract apply flow URL
  - SmartRecruiters: construct apply URL

- [ ] **ATS metadata enrichment**
  - Required fields per ATS (resume, cover letter, portfolio)
  - Application method (direct URL, email, form)
  - Estimated application complexity

- [ ] **Company research integration**
  - Wikipedia summary (from legacy script)
  - LinkedIn company page data
  - Glassdoor ratings
  - Crunchbase funding info
  - Company size and stage

### Medium Priority

- [ ] **Resume tailoring suggestions**
  - Keyword gap analysis (job description vs resume)
  - Skill match highlighting
  - Cover letter template generation

- [ ] **Application tracking**
  - SQLite database for application history
  - Status tracking (applied, interview, offer, rejected)
  - Follow-up reminders
  - Application timeline visualization

## Phase 3 - Scoring & Ranking

### High Priority

- [ ] **Scoring engine rewrite**
  - Replace binary filtering with weighted scoring
  - Configurable scoring weights via TOML
  - Multiple scoring dimensions:
    - Title match quality (exact, partial, keyword)
    - Skills match (percentage of required skills)
    - Experience level alignment
    - Salary fit (within range, above minimum)
    - Location preference fit
    - Company quality signals
    - Job recency
    - ATS platform preference

- [ ] **Explainability**
  - Per-job score breakdown
  - Why this job matched (which keywords, skills)
  - Why this job was filtered out
  - Confidence scores

- [ ] **Ranking algorithms**
  - Multi-factor ranking
  - Personalized ranking (learn from user feedback)
  - Diversity in results (mix of companies, roles, sources)

### Medium Priority

- [ ] **Skill extraction from descriptions**
  - NLP-based skill extraction (even without external libs, basic pattern matching)
  - Technology stack detection
  - Experience level inference (junior/mid/senior/staff)

- [ ] **Salary normalization**
  - Parse salary ranges from descriptions
  - Currency conversion
  - Cost-of-living adjustment
  - Compensation tier classification

## Later - Apply-Assist & Automation

### High Priority

- [ ] **Safe apply-assist workflow**
  - Generate pre-filled application forms
  - Resume upload helper
  - Cover letter generation with job-specific customization
  - **Hard confirmation gate** before any submission
  - No fully automated submissions

- [ ] **Browser automation (optional)**
  - Fill application forms (with user review)
  - Capture application confirmation
  - Screenshot for record-keeping
  - Only with explicit user approval per action

### Medium Priority

- [ ] **Notification system**
  - Email alerts for new matching jobs
  - Slack/Discord webhook integration
  - Daily/weekly digest generation
  - Scheduled execution via cron or systemd

- [ ] **Analytics dashboard**
  - Search history and trends
  - Application funnel metrics
  - Response rate tracking
  - Time-to-application statistics

## Architecture Improvements

### High Priority

- [ ] **Plugin system for collectors**
  - Dynamic collector loading
  - Third-party collector packages
  - Configuration-driven collector enablement

- [ ] **Persistent storage**
  - SQLite for job records and application history
  - Migration system
  - Backup/restore

- [ ] **Configuration management**
  - Schema validation for TOML files
  - Config version migration
  - Interactive config editor

### Medium Priority

- [ ] **Containerization**
  - Docker image for easy deployment
  - Docker Compose for scheduled runs
  - Kubernetes CronJob example

- [ ] **API server**
  - REST API wrapper around CLI functionality
  - GraphQL endpoint for flexible queries
  - Webhook support for real-time job alerts

## Performance & Reliability

- [ ] **Concurrent fetching**
  - ThreadPoolExecutor for parallel collectors
  - AsyncIO rewrite (if external deps allowed later)
  - Connection pooling

- [ ] **Error resilience**
  - Circuit breaker pattern for failing sources
  - Retry with exponential backoff
  - Partial result handling (return what succeeded)

- [ ] **Monitoring**
  - Per-source success/failure metrics
  - Response time tracking
  - Data quality scoring
  - Health check endpoint

## Community & Ecosystem

- [ ] **Company database**
  - Community-curated company profiles
  - ATS platform detection feedback
  - Company hiring status
  - Salary data crowdsourcing

- [ ] **Template marketplace**
  - Profile templates for different roles
  - Resume templates
  - Cover letter templates
  - Scoring configuration templates

- [ ] **Integration guides**
  - Zapier / Make.com integration
  - Notion database sync
  - Airtable integration
  - Google Sheets automation

## Contributing to the Roadmap

To propose a new feature or improvement:

1. Open an issue with the `enhancement` label
2. Describe the use case and expected behavior
3. Note which phase it belongs to (or if it crosses phases)
4. If you're willing to implement it, mention that

Priority is determined by:
- User demand (upvotes on issues)
- Alignment with project philosophy (free, open, no external deps where possible)
- Technical feasibility within phase constraints
- Impact on job hunting effectiveness
