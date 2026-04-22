from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


CollectorFn = Callable[[], list[dict[str, Any]]]


class CollectorRegistry:
    """Tiny registry for local ingestion sources.

    Maps source names to callables that return raw job records.
    No plugin framework; explicit registration only.
    Supports sequential and concurrent collection.
    """

    def __init__(self) -> None:
        self._collectors: dict[str, CollectorFn] = {}

    def register(self, name: str, fn: CollectorFn) -> None:
        """Register a collector callable under a source name."""
        self._collectors[name] = fn

    def collect(
        self,
        enabled_sources: dict[str, bool],
        errors: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Run all enabled collectors sequentially and concatenate results."""
        records: list[dict[str, Any]] = []
        for name, enabled in enabled_sources.items():
            if enabled and name in self._collectors:
                try:
                    records.extend(self._collectors[name]())
                except Exception as exc:
                    if errors is not None:
                        errors[name] = str(exc)
        return records

    def collect_concurrent(
        self,
        enabled_sources: dict[str, bool],
        errors: dict[str, str] | None = None,
        max_workers: int | None = None,
    ) -> list[dict[str, Any]]:
        """Run all enabled collectors concurrently and concatenate results."""
        active_collectors = {
            name: fn
            for name, enabled in enabled_sources.items()
            if enabled and name in self._collectors
            for fn in [self._collectors[name]]
        }

        if not active_collectors:
            return []

        records: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(fn): name
                for name, fn in active_collectors.items()
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    records.extend(result)
                except Exception as exc:
                    if errors is not None:
                        errors[name] = str(exc)

        return records

    def available_sources(self) -> set[str]:
        """Return the set of registered source names."""
        return set(self._collectors.keys())
