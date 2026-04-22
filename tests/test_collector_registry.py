from __future__ import annotations

import unittest
from typing import Any

from jobforager.collectors import CollectorRegistry


class TestCollectorRegistry(unittest.TestCase):
    def test_registry_collects_enabled_sources(self) -> None:
        registry = CollectorRegistry()
        registry.register("a", lambda: [{"source": "a", "title": "t1", "company": "c", "job_url": "u"}])
        registry.register("b", lambda: [{"source": "b", "title": "t2", "company": "c", "job_url": "u"}])

        results = registry.collect({"a": True, "b": False})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "a")

    def test_registry_concatenates_multiple_enabled(self) -> None:
        registry = CollectorRegistry()
        registry.register("a", lambda: [{"source": "a", "title": "t1", "company": "c", "job_url": "u"}])
        registry.register("b", lambda: [{"source": "b", "title": "t2", "company": "c", "job_url": "u"}])

        results = registry.collect({"a": True, "b": True})
        self.assertEqual(len(results), 2)

    def test_registry_ignores_unregistered_sources(self) -> None:
        registry = CollectorRegistry()
        registry.register("a", lambda: [{"source": "a", "title": "t", "company": "c", "job_url": "u"}])

        results = registry.collect({"a": True, "external": True})
        self.assertEqual(len(results), 1)

    def test_registry_returns_empty_when_none_enabled(self) -> None:
        registry = CollectorRegistry()
        registry.register("a", lambda: [{"source": "a", "title": "t", "company": "c", "job_url": "u"}])

        results = registry.collect({"a": False})
        self.assertEqual(results, [])

    def test_available_sources(self) -> None:
        registry = CollectorRegistry()
        registry.register("a", lambda: [])
        registry.register("b", lambda: [])

        self.assertEqual(registry.available_sources(), {"a", "b"})

    def test_registry_isolates_failed_collectors(self) -> None:
        registry = CollectorRegistry()
        registry.register(
            "good",
            lambda: [{"source": "good", "title": "t", "company": "c", "job_url": "u"}],
        )
        registry.register("bad", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

        errors: dict[str, str] = {}
        results = registry.collect({"good": True, "bad": True}, errors=errors)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "good")
        self.assertIn("bad", errors)

    def test_registry_captures_error_messages(self) -> None:
        registry = CollectorRegistry()
        registry.register(
            "a", lambda: (_ for _ in ()).throw(ValueError("something went wrong"))
        )

        errors: dict[str, str] = {}
        results = registry.collect({"a": True}, errors=errors)

        self.assertEqual(results, [])
        self.assertEqual(errors.get("a"), "something went wrong")


if __name__ == "__main__":
    unittest.main()
