from __future__ import annotations

import unittest
from unittest.mock import patch

from jobforager.company_lists import (
    _extract_slug_from_url,
    get_ashby_boards,
    get_greenhouse_tokens,
    get_lever_slugs,
)


class TestExtractSlugFromUrl(unittest.TestCase):
    def test_greenhouse(self) -> None:
        self.assertEqual(
            _extract_slug_from_url("https://boards.greenhouse.io/stripe"),
            "stripe",
        )

    def test_greenhouse_job_boards(self) -> None:
        self.assertEqual(
            _extract_slug_from_url("https://job-boards.greenhouse.io/airbnb"),
            "airbnb",
        )

    def test_lever(self) -> None:
        self.assertEqual(
            _extract_slug_from_url("https://jobs.lever.co/netflix"),
            "netflix",
        )

    def test_ashby(self) -> None:
        self.assertEqual(
            _extract_slug_from_url("https://jobs.ashbyhq.com/supabase"),
            "supabase",
        )

    def test_unknown(self) -> None:
        self.assertIsNone(
            _extract_slug_from_url("https://example.com/jobs"),
        )

    def test_trailing_slash(self) -> None:
        self.assertEqual(
            _extract_slug_from_url("https://boards.greenhouse.io/stripe/"),
            "stripe",
        )


class TestGetGreenhouseTokens(unittest.TestCase):
    def test_returns_defaults_when_fetch_fails(self) -> None:
        with patch(
            "jobforager.company_lists._fetch_json",
            side_effect=IOError("network down"),
        ):
            tokens = get_greenhouse_tokens()
        self.assertIsInstance(tokens, list)
        self.assertIn("airbnb", tokens)

    def test_returns_fetched_data(self) -> None:
        with patch(
            "jobforager.company_lists._fetch_json",
            return_value=["stripe", "figma", "anthropic"],
        ):
            tokens = get_greenhouse_tokens()
        self.assertEqual(tokens, ["stripe", "figma", "anthropic"])


class TestGetLeverSlugs(unittest.TestCase):
    def test_returns_defaults_when_fetch_fails(self) -> None:
        with patch(
            "jobforager.company_lists._fetch_json",
            side_effect=IOError("network down"),
        ):
            slugs = get_lever_slugs()
        self.assertIsInstance(slugs, list)
        self.assertIn("airbnb", slugs)

    def test_returns_fetched_data(self) -> None:
        with patch(
            "jobforager.company_lists._fetch_json",
            return_value=["netflix", "shopify"],
        ):
            slugs = get_lever_slugs()
        self.assertEqual(slugs, ["netflix", "shopify"])


class TestGetAshbyBoards(unittest.TestCase):
    def test_returns_defaults_when_fetch_fails(self) -> None:
        with patch(
            "jobforager.company_lists._fetch_json",
            side_effect=IOError("network down"),
        ):
            boards = get_ashby_boards()
        self.assertIsInstance(boards, list)
        self.assertIn("supabase", boards)

    def test_returns_fetched_data(self) -> None:
        with patch(
            "jobforager.company_lists._fetch_json",
            return_value=["ramp", "linear"],
        ):
            boards = get_ashby_boards()
        self.assertEqual(boards, ["ramp", "linear"])


if __name__ == "__main__":
    unittest.main()
