from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-forager",
        description="Job Forager CLI (Phase 1.2 ingestion foundation)",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("help", help="Show scaffold status.")

    hunt_parser = subparsers.add_parser(
        "hunt", help="Run ingestion foundation checks (Phase 1.2)."
    )
    hunt_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run a local sample ingestion/normalization/dedupe flow.",
    )
    hunt_parser.add_argument(
        "--profile",
        default="config/profile.example.toml",
        help="Path to profile TOML file (default: config/profile.example.toml).",
    )
    hunt_parser.add_argument(
        "--records",
        default=None,
        help=(
            "Path to JSON, JSONL, or CSV file with raw job records "
            "(default: use built-in sample records)."
        ),
    )
    hunt_parser.add_argument(
        "--output-json",
        dest="output_json",
        default=None,
        help="Path to write normalized records as JSON.",
    )
    hunt_parser.add_argument(
        "--output-csv",
        dest="output_csv",
        default=None,
        help="Path to write normalized records as CSV.",
    )

    validate_parser = subparsers.add_parser(
        "validate", help="Validate a profile TOML file."
    )
    validate_parser.add_argument(
        "--profile",
        default="config/profile.example.toml",
        help="Path to profile TOML file (default: config/profile.example.toml).",
    )

    search_parser = subparsers.add_parser(
        "search",
        help=(
            "Search live job sources (remotive, hackernews, remoteok, "
            "arbeitnow, greenhouse, lever, ashby, smartrecruiters, workday, "
            "hiringcafe, linkedin, indeed, glassdoor)."
        ),
    )
    search_parser.add_argument(
        "--keywords",
        default=None,
        help="Comma-separated keywords to match in title, company, tags, description.",
    )
    search_parser.add_argument(
        "--title-keywords",
        default=None,
        help="Comma-separated keywords to match ONLY in job titles.",
    )
    search_parser.add_argument(
        "--desc-keywords",
        default=None,
        help="Comma-separated keywords to match ONLY in job descriptions.",
    )
    search_parser.add_argument(
        "--exclude",
        default=None,
        help="Comma-separated keywords to EXCLUDE from results.",
    )
    search_parser.add_argument(
        "--location",
        default=None,
        help="Free-text location filter.",
    )
    search_parser.add_argument(
        "--level",
        default=None,
        choices=["intern", "entry", "mid", "senior"],
        help="Filter by experience level extracted from job title.",
    )
    search_parser.add_argument(
        "--hide-recruiters",
        dest="hide_recruiters",
        action="store_true",
        help="Hide jobs from staffing agencies and recruiting firms.",
    )
    search_parser.add_argument(
        "--since",
        default=None,
        help="Only show jobs posted on or after this date (YYYY-MM-DD).",
    )
    search_parser.add_argument(
        "--last",
        dest="last_duration",
        default=None,
        help="Duration window, e.g. 24h, 7d, 30d.",
    )
    search_parser.add_argument(
        "--sources",
        default="remotive,hackernews",
        help=(
            "Comma-separated source list. Available: remotive, hackernews, "
            "remoteok, arbeitnow, greenhouse, lever, ashby, smartrecruiters, "
            "workday, hiringcafe, linkedin, indeed, glassdoor. "
            "(default: remotive,hackernews)."
        ),
    )
    search_parser.add_argument(
        "--profile",
        default=None,
        help="Optional path to profile TOML for additional filtering.",
    )
    search_parser.add_argument(
        "--workers",
        type=int,
        default=30,
        help="Number of concurrent threads for multi-company sources (default: 30).",
    )
    search_parser.add_argument(
        "--output-json",
        dest="output_json",
        default=None,
        help="Path to write normalized records as JSON.",
    )
    search_parser.add_argument(
        "--output-csv",
        dest="output_csv",
        default=None,
        help="Path to write normalized records as CSV.",
    )

    return parser
