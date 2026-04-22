# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 10 live job source collectors (Remotive, Hacker News, RemoteOK, ArbeitNow, Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Hiring.cafe)
- Concurrent fetching with configurable ThreadPoolExecutor workers
- Profile-based filtering (titles, skills, locations, salary, remote preference)
- Advanced CLI filters: `--exclude`, `--level`, `--hide-recruiters`
- TOML profile configuration support
- JSON/CSV export
- URL validation
- Deduplication by composite key + URL
- ATS auto-detection
- Zero external dependencies (Python standard library only)

### Changed
- Complete rebrand from job-forager to job-forager
- Modular architecture: split CLI into parser/commands/pipeline/formatters/samples
- Documentation overhaul with professional OSS standards

## [0.1.0] - 2026-04-22

### Added
- Initial release
- CLI with search, hunt, validate, help commands
- 4 base job sources (Remotive, ArbeitNow, RemoteOK, The Muse)
- Profile loader with INI/TOML support
- Normalization and deduplication pipeline
- JSON/CSV exporters
