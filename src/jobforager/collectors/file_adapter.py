from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def load_raw_records_from_file(path: str | Path) -> list[dict[str, Any]]:
    """Load raw job records from a JSON, JSONL, or CSV file.

    Supports:
    - JSON list: [{...}, {...}]
    - JSON object with a list key: {"jobs": [{...}, {...}]}
    - JSONL: one JSON object per line
    - CSV: header row with columns matching raw record fields
    """
    file_path = Path(path)
    content = file_path.read_text(encoding="utf-8")

    if file_path.suffix.lower() == ".csv":
        return _parse_csv(content)

    # Try JSON first
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        records = _parse_jsonl(content)
        if not records:
            raise ValueError(f"File {file_path} is not valid JSON or JSONL.")
        return records

    if isinstance(data, list):
        return _validate_records(data, file_path)

    if isinstance(data, dict):
        for key in ("jobs", "records", "data"):
            if key in data and isinstance(data[key], list):
                return _validate_records(data[key], file_path)
        if _looks_like_record(data):
            return [data]
        raise ValueError(
            f"JSON object in {file_path} must contain a list under "
            "'jobs', 'records', or 'data'."
        )

    raise ValueError(f"Unsupported JSON structure in {file_path}.")


def _parse_csv(content: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    reader = csv.DictReader(content.splitlines())
    for row in reader:
        record: dict[str, Any] = {}
        for key, value in row.items():
            if value is None:
                continue
            stripped = value.strip()
            if not stripped:
                continue
            if key == "tags":
                record[key] = [t.strip() for t in stripped.split("|") if t.strip()]
            else:
                record[key] = stripped
        records.append(record)
    return records


def _parse_jsonl(content: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_num, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_num}: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(
                f"Expected JSON object on line {line_num}, got {type(obj).__name__}."
            )
        records.append(obj)
    return records


def _validate_records(items: list[Any], file_path: Path) -> list[dict[str, Any]]:
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(
                f"Item at index {idx} in {file_path} is not a JSON object."
            )
    return items  # type: ignore[return-value]


def _looks_like_record(data: dict[str, Any]) -> bool:
    return all(k in data for k in ("source", "title", "company", "job_url"))
