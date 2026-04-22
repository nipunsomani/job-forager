from __future__ import annotations

import csv
import json
import unittest
from datetime import datetime
from pathlib import Path

from jobforager.exporters import write_normalized_csv, write_normalized_json
from jobforager.models import JobRecord


class TestNormalizedExporter(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(__file__).resolve().parent / ".tmp"
        self.tmp_dir.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        for path in self.tmp_dir.iterdir():
            if path.is_file():
                path.unlink()

    def test_write_normalized_json(self) -> None:
        job = JobRecord(
            source="remotive",
            title="Senior Python Engineer",
            company="Example Labs",
            job_url="https://jobs.example.com/roles/1",
            tags=["python", "fastapi"],
        )
        path = self.tmp_dir / "out.json"
        write_normalized_json([job], ["key-1"], path)

        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["source"], "remotive")
        self.assertEqual(data[0]["dedupe_key"], "key-1")
        self.assertEqual(data[0]["tags"], ["python", "fastapi"])

    def test_write_normalized_json_datetime(self) -> None:
        posted = datetime(2024, 1, 15, 10, 30, 0)
        job = JobRecord(
            source="remotive",
            title="T",
            company="C",
            job_url="U",
            posted_at=posted,
        )
        path = self.tmp_dir / "out_dt.json"
        write_normalized_json([job], ["k"], path)

        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data[0]["posted_at"], "2024-01-15T10:30:00")

    def test_write_normalized_csv(self) -> None:
        job = JobRecord(
            source="remotive",
            title="Senior Python Engineer",
            company="Example Labs",
            job_url="https://jobs.example.com/roles/1",
            tags=["python", "fastapi"],
        )
        path = self.tmp_dir / "out.csv"
        write_normalized_csv([job], ["key-1"], path)

        text = path.read_text(encoding="utf-8")
        reader = csv.DictReader(text.splitlines())
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dedupe_key"], "key-1")
        self.assertEqual(rows[0]["source"], "remotive")
        self.assertEqual(rows[0]["tags"], "python|fastapi")

    def test_write_normalized_csv_empty(self) -> None:
        path = self.tmp_dir / "empty.csv"
        write_normalized_csv([], [], path)
        self.assertEqual(path.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
