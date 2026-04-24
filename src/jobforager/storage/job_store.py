from __future__ import annotations

import json
import os
import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_JOBS_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    job_url TEXT NOT NULL UNIQUE,
    location TEXT,
    remote_type TEXT,
    salary_raw TEXT,
    salary_min_usd INTEGER,
    salary_max_usd INTEGER,
    posted_at TEXT,
    description TEXT,
    tags TEXT,
    metadata TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at TEXT NOT NULL,
    sources TEXT NOT NULL,
    keywords TEXT,
    new_jobs_count INTEGER
);
"""


def _default_db_path() -> str:
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA", str(Path.home()))
        path = Path(base) / "jobforager" / "jobs.db"
    else:
        path = Path.home() / ".cache" / "jobforager" / "jobs.db"
    return str(path)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.path = db_path or _default_db_path()
        self._ensure_parent()
        self._ensure_schema()

    def _ensure_parent(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    def _ensure_schema(self) -> None:
        conn = sqlite3.connect(self.path)
        try:
            conn.executescript(_JOBS_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def upsert_jobs(self, jobs: list[dict[str, Any]]) -> tuple[int, int]:
        inserted = 0
        updated = 0
        now = _now_iso()

        if not jobs:
            return 0, 0

        conn = sqlite3.connect(self.path)
        try:
            urls = [j["job_url"] for j in jobs if j.get("job_url")]
            if urls:
                placeholders = ",".join("?" * len(urls))
                existing_rows = conn.execute(
                    f"SELECT job_url FROM jobs WHERE job_url IN ({placeholders})",
                    urls,
                ).fetchall()
                existing = {row[0] for row in existing_rows}
            else:
                existing = set()

            for job in jobs:
                job_url = job.get("job_url")
                if not job_url:
                    continue

                posted_at = job.get("posted_at")
                if isinstance(posted_at, datetime):
                    posted_at = posted_at.isoformat()

                tags = job.get("tags")
                metadata = job.get("metadata", {})

                params = (
                    job.get("source"),
                    job.get("external_id"),
                    job.get("title"),
                    job.get("company"),
                    job_url,
                    job.get("location"),
                    job.get("remote_type"),
                    job.get("salary_raw"),
                    job.get("salary_min_usd"),
                    job.get("salary_max_usd"),
                    posted_at,
                    job.get("description"),
                    json.dumps(tags) if tags is not None else "[]",
                    json.dumps(metadata) if metadata is not None else "{}",
                    now,
                    now,
                )

                if job_url in existing:
                    conn.execute(
                        "UPDATE jobs SET last_seen_at = ? WHERE job_url = ?",
                        (now, job_url),
                    )
                    updated += 1
                else:
                    conn.execute(
                        """
                        INSERT INTO jobs (
                            source, external_id, title, company, job_url,
                            location, remote_type, salary_raw, salary_min_usd,
                            salary_max_usd, posted_at, description, tags,
                            metadata, first_seen_at, last_seen_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        params,
                    )
                    inserted += 1

            conn.commit()
        finally:
            conn.close()

        return inserted, updated

    def get_jobs_since(self, since: datetime) -> list[dict[str, Any]]:
        since_str = since.isoformat()
        conn = sqlite3.connect(self.path)
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM jobs WHERE first_seen_at > ? ORDER BY first_seen_at DESC",
                (since_str,),
            ).fetchall()

            results: list[dict[str, Any]] = []
            for row in rows:
                record = dict(row)
                record["tags"] = json.loads(record.get("tags") or "[]")
                record["metadata"] = json.loads(record.get("metadata") or "{}")
                if record.get("posted_at"):
                    try:
                        record["posted_at"] = datetime.fromisoformat(record["posted_at"])
                    except ValueError:
                        pass
                results.append(record)
            return results
        finally:
            conn.close()

    def get_last_run_time(self) -> datetime | None:
        conn = sqlite3.connect(self.path)
        try:
            row = conn.execute("SELECT MAX(run_at) FROM run_log").fetchone()
            if row and row[0]:
                return datetime.fromisoformat(row[0])
            return None
        finally:
            conn.close()

    def record_run(
        self,
        sources: list[str],
        keywords: str | None,
        new_jobs_count: int,
    ) -> None:
        now = _now_iso()
        conn = sqlite3.connect(self.path)
        try:
            conn.execute(
                "INSERT INTO run_log (run_at, sources, keywords, new_jobs_count) VALUES (?, ?, ?, ?)",
                (now, ",".join(sources), keywords, new_jobs_count),
            )
            conn.commit()
        finally:
            conn.close()
