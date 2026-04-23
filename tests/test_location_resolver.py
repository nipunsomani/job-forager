from __future__ import annotations

import unittest

from jobforager.normalize.location_resolver import (
    normalize_location,
    location_matches,
)


class TestNormalizeLocation(unittest.TestCase):
    def test_uk_variants(self) -> None:
        self.assertIn("uk", normalize_location("UK"))
        self.assertIn("uk", normalize_location("United Kingdom"))
        self.assertIn("uk", normalize_location("GB"))
        self.assertIn("uk", normalize_location("England"))
        self.assertIn("uk", normalize_location("Scotland"))
        self.assertIn("uk", normalize_location("Wales"))

    def test_us_variants(self) -> None:
        self.assertIn("us", normalize_location("US"))
        self.assertIn("us", normalize_location("USA"))
        self.assertIn("us", normalize_location("United States"))

    def test_city_to_country(self) -> None:
        self.assertIn("uk", normalize_location("London"))
        self.assertIn("uk", normalize_location("London, UK"))
        self.assertIn("us", normalize_location("New York"))
        self.assertIn("us", normalize_location("San Francisco, CA"))
        self.assertIn("canada", normalize_location("Toronto"))
        self.assertIn("germany", normalize_location("Berlin"))

    def test_remote_token(self) -> None:
        tokens = normalize_location("Remote")
        self.assertIn("remote", tokens)
        tokens = normalize_location("Remote - UK")
        self.assertIn("remote", tokens)
        self.assertIn("uk", tokens)
        tokens = normalize_location("Remote, US")
        self.assertIn("remote", tokens)
        self.assertIn("us", tokens)

    def test_none_and_empty(self) -> None:
        self.assertEqual(normalize_location(None), set())
        self.assertEqual(normalize_location(""), set())

    def test_multiple_locations(self) -> None:
        tokens = normalize_location("London, England, United Kingdom")
        self.assertIn("uk", tokens)
        self.assertIn("london", tokens)


class TestLocationMatches(unittest.TestCase):
    def test_none_job_location_matches(self) -> None:
        self.assertTrue(location_matches(None, ["UK"]))

    def test_empty_query_matches(self) -> None:
        self.assertTrue(location_matches("London", []))

    def test_uk_matches_variants(self) -> None:
        self.assertTrue(location_matches("London, UK", ["UK"]))
        self.assertTrue(location_matches("United Kingdom", ["UK"]))
        self.assertTrue(location_matches("England", ["UK"]))
        self.assertTrue(location_matches("London", ["UK"]))
        self.assertTrue(location_matches("Remote, UK", ["UK"]))
        self.assertTrue(location_matches("Remote - United Kingdom", ["UK"]))

    def test_uk_query_matches_london(self) -> None:
        self.assertTrue(location_matches("London", ["UK"]))
        self.assertTrue(location_matches("Manchester", ["UK"]))
        self.assertTrue(location_matches("Bristol, UK", ["UK"]))

    def test_london_query_matches_london_variants(self) -> None:
        self.assertTrue(location_matches("London", ["London"]))
        self.assertTrue(location_matches("London, UK", ["London"]))
        self.assertTrue(location_matches("London, England", ["London"]))

    def test_us_does_not_match_uk(self) -> None:
        self.assertFalse(location_matches("New York", ["UK"]))
        self.assertFalse(location_matches("Remote - US", ["UK"]))
        self.assertFalse(location_matches("United States", ["UK"]))

    def test_plain_remote_matches_any_query(self) -> None:
        self.assertTrue(location_matches("Remote", ["UK"]))
        self.assertTrue(location_matches("Remote", ["US"]))
        self.assertTrue(location_matches("Remote", ["London"]))

    def test_qualified_remote_does_not_match_wrong_country(self) -> None:
        self.assertFalse(location_matches("Remote - US", ["UK"]))
        self.assertFalse(location_matches("Remote, UK", ["US"]))
        self.assertFalse(location_matches("US Remote", ["UK"]))

    def test_qualified_remote_matches_same_country(self) -> None:
        self.assertTrue(location_matches("Remote - UK", ["UK"]))
        self.assertTrue(location_matches("Remote, US", ["US"]))
        self.assertTrue(location_matches("UK - Remote", ["UK"]))

    def test_multiple_query_locations(self) -> None:
        self.assertTrue(location_matches("London", ["UK", "Germany"]))
        self.assertTrue(location_matches("Berlin", ["UK", "Germany"]))
        self.assertFalse(location_matches("Paris", ["UK", "Germany"]))


if __name__ == "__main__":
    unittest.main()
