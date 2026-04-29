# AGENTS.md

## Project

This repo is the active implementation repo for `job-forager`.

**Goal**: Build the best free, open-source job hunting automation tool by evolving the original `job-forager` in small, safe phases.

**Current Status**: Phase 1.x - Ingestion Foundation. 10 live job collectors, 214 tests passing, zero external dependencies.

## Repository Structure

This is the primary implementation repository for `job-forager`.

## Product direction

Target system capabilities over time:
- discover jobs from multiple sources
- normalize and dedupe records
- classify ATS/apply types
- rank jobs against candidate preferences
- build a safe apply-assist workflow
- require explicit confirmation before any submission action

## Completed phases

- Phase 0: scaffold/foundation
- Phase 1.1: canonical dataclass models (JobRecord, CandidateProfile)
- Phase 1.2: profile loader, normalization contract, dedupe utility, `hunt --dry-run` CLI
- Phase 1.x (current): ingestion + normalization foundation
  - 10 live job collectors (Remotive, HN, RemoteOK, ArbeitNow, Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Hiring.cafe)
  - Company list auto-discovery (10,000+ companies)
  - ATS auto-detection (7 platforms)
  - Profile-based filtering
  - URL validation
  - JSON/CSV export
  - 186 unit tests

## Current architecture

- `src/jobforager/models/` → canonical dataclass models (JobRecord, CandidateProfile)
- `src/jobforager/config/` → TOML profile loading
- `src/jobforager/normalize/` → raw-job normalization, dedupe, filtering, ATS detection
- `src/jobforager/search/` → job source collectors (9 platforms)
- `src/jobforager/collectors/` → CollectorRegistry and base classes
- `src/jobforager/exporters/` → JSON/CSV output writers
- `src/jobforager/company_lists.py` → fetch/cache public company lists
- `src/jobforager/cli/` → CLI entry point and search flow


## Planned roadmap

- Phase 1.x → ingestion + normalization foundation (IN PROGRESS)
- Phase 2 → ATS detection and apply-routing metadata, no submission automation
- Phase 3 → scoring/ranking and explainability
- Later → safe apply-assist flows with hard confirmation gates

See `docs/ROADMAP.md` for detailed planned improvements.

## Safe to work on

- Only the next explicitly approved phase
- Small utilities, loaders, normalizers, CLI improvements, tests, and docs within the approved phase
- Compatibility-preserving cleanup that does not broaden scope
- New collectors within Phase 1.x

## Out of scope right now

- ATS automation
- browser automation
- job submission
- broad refactors
- cross-repo merge work
- scoring/ranking outside the approved phase
- storage/database expansion outside the approved phase
- live external integrations unless explicitly requested

## Non-negotiable rules

- Keep changes small, reversible, and phase-scoped
- Preserve legacy behavior where practical
- Prefer Python standard library and simple abstractions
- Prefer pure functions for normalization/utility logic
- Use snake_case naming
- Add or update tests for meaningful behavior changes
- If a task crosses phase boundaries, stop and ask first
- If repo state and instructions conflict, trust the actual repo and update docs minimally

## Validation

Run after meaningful changes:
- `python -m compileall src`
- `PYTHONPATH=src python -m jobforager.cli help`
- `PYTHONPATH=src python -m unittest discover -s tests -v`

For current dry-run flow:
- `PYTHONPATH=src python -m jobforager.cli hunt --dry-run --profile config/profile.example.toml`

## Git workflow

- Use feature branches, not direct work on `main`
- Make small commits grouped by concern
- Do not rewrite unrelated files
- Keep the working tree clean before starting a new phase

## When uncertain

Before coding, summarize:
1) current repo state
2) current approved phase
3) what is safe to implement next
4) what is explicitly out of scope

Ask for approval before crossing phase boundaries.

## Documentation references

- `README.md` - Project overview, quick start, features
- `dev-docs/architecture.md` - Module structure and data flow
- `docs/CLI_REFERENCE.md` - All CLI commands and flags
- `docs/API_SOURCES.md` - Collector API documentation
- `docs/ROADMAP.md` - Future improvements and extensions
- `dev-docs/safety-policy.md` - Safety constraints
