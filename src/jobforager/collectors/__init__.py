"""Collectors package for job-forager."""

from .file_adapter import load_raw_records_from_file
from .registry import CollectorRegistry

__all__ = ["CollectorRegistry", "load_raw_records_from_file"]
