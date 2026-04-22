from __future__ import annotations

import json
import unittest
import uuid
from pathlib import Path

from jobforager.collectors import load_raw_records_from_file


class TestFileAdapter(unittest.TestCase):
    def _write_file(self, content: str, suffix: str = ".json") -> Path:
        tests_root = Path(__file__).resolve().parent
        path = tests_root / f"file_adapter_tmp_{uuid.uuid4().hex}{suffix}"
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        path.write_text(content, encoding="utf-8")
        return path

    def test_load_json_list(self) -> None:
        records = [
            {"source": "a", "title": "t", "company": "c", "job_url": "u"}
        ]
        path = self._write_file(json.dumps(records))
        result = load_raw_records_from_file(path)
        self.assertEqual(result, records)

    def test_load_json_wrapped_dict(self) -> None:
        records = [
            {"source": "a", "title": "t", "company": "c", "job_url": "u"}
        ]
        path = self._write_file(json.dumps({"jobs": records}))
        result = load_raw_records_from_file(path)
        self.assertEqual(result, records)

    def test_load_jsonl(self) -> None:
        lines = [
            '{"source": "a", "title": "t1", "company": "c", "job_url": "u1"}',
            '{"source": "b", "title": "t2", "company": "c", "job_url": "u2"}',
        ]
        path = self._write_file("\n".join(lines), suffix=".jsonl")
        result = load_raw_records_from_file(path)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "t1")
        self.assertEqual(result[1]["title"], "t2")

    def test_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_raw_records_from_file("nonexistent.json")

    def test_invalid_json(self) -> None:
        path = self._write_file("not json")
        with self.assertRaises(ValueError):
            load_raw_records_from_file(path)

    def test_single_record_dict(self) -> None:
        record = {
            "source": "a",
            "title": "t",
            "company": "c",
            "job_url": "u",
            "extra": 1,
        }
        path = self._write_file(json.dumps(record))
        result = load_raw_records_from_file(path)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["extra"], 1)

    def test_load_csv(self) -> None:
        csv_content = (
            "source,title,company,job_url,location,remote_type\n"
            "remotive,Engineer,Example,https://example.com/1,City,remote\n"
            "themuse,Designer,Data Co,https://example.com/2,Town,hybrid\n"
        )
        path = self._write_file(csv_content, suffix=".csv")
        result = load_raw_records_from_file(path)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["source"], "remotive")
        self.assertEqual(result[0]["title"], "Engineer")
        self.assertEqual(result[0]["location"], "City")
        self.assertEqual(result[1]["remote_type"], "hybrid")

    def test_load_csv_with_pipe_separated_tags(self) -> None:
        csv_content = (
            "source,title,company,job_url,tags\n"
            "remotive,Engineer,Example,https://example.com/1,python|fastapi\n"
        )
        path = self._write_file(csv_content, suffix=".csv")
        result = load_raw_records_from_file(path)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tags"], ["python", "fastapi"])

    def test_load_csv_empty_rows(self) -> None:
        csv_content = "source,title,company,job_url\n"
        path = self._write_file(csv_content, suffix=".csv")
        result = load_raw_records_from_file(path)
        self.assertEqual(result, [])

    def test_load_csv_ignores_blank_cells(self) -> None:
        csv_content = (
            "source,title,company,job_url,location\n"
            "remotive,Engineer,Example,https://example.com/1,\n"
        )
        path = self._write_file(csv_content, suffix=".csv")
        result = load_raw_records_from_file(path)
        self.assertEqual(len(result), 1)
        self.assertNotIn("location", result[0])


if __name__ == "__main__":
    unittest.main()
