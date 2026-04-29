from __future__ import annotations

import unittest
from unittest.mock import patch

from jobforager.company_lists import (
    _extract_slug_from_url,
    get_ashby_boards,
    get_greenhouse_tokens,
    get_lever_slugs,
    get_smartrecruiters_slugs,
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

    def test_smartrecruiters(self) -> None:
        self.assertEqual(
            _extract_slug_from_url("https://jobs.smartrecruiters.com/adobe1"),
            "adobe1",
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
        ), patch(
            "jobforager.company_lists._load_local_json",
            return_value=None,
        ):
            tokens = get_greenhouse_tokens()
        self.assertIsInstance(tokens, list)
        self.assertIn("airbnb", tokens)

    def test_returns_merged_defaults_and_fetched(self) -> None:
        with patch(
            "jobforager.company_lists._fetch_json",
            return_value=["stripe", "figma", "anthropic"],
        ), patch(
            "jobforager.company_lists._load_local_json",
            return_value=None,
        ), patch(
            "jobforager.company_lists._save_local_json",
        ) as mock_save:
            tokens = get_greenhouse_tokens()
        expected = sorted(
            set(
                ["airbnb", "stripe", "figma", "anthropic", "hootsuite", "canonical", "wehrtyou", "monzo", "tide"]
                + ["stripe", "figma", "anthropic"]
            )
        )
        self.assertEqual(tokens, expected)
        mock_save.assert_called_once()


class TestGetLeverSlugs(unittest.TestCase):
    def test_returns_defaults_when_fetch_fails(self) -> None:
        with patch(
            "jobforager.company_lists._fetch_json",
            side_effect=IOError("network down"),
        ), patch(
            "jobforager.company_lists._load_local_json",
            return_value=None,
        ):
            slugs = get_lever_slugs()
        self.assertIsInstance(slugs, list)
        self.assertIn("airbnb", slugs)

    def test_returns_merged_defaults_and_fetched(self) -> None:
        with patch(
            "jobforager.company_lists._fetch_json",
            return_value=["netflix", "shopify"],
        ), patch(
            "jobforager.company_lists._load_local_json",
            return_value=None,
        ), patch(
            "jobforager.company_lists._save_local_json",
        ) as mock_save:
            slugs = get_lever_slugs()
        expected = sorted(
            set(
                ["airbnb", "netflix", "shopify", "leverdemo", "zopa"]
                + ["netflix", "shopify"]
            )
        )
        self.assertEqual(slugs, expected)
        mock_save.assert_called_once()


class TestGetAshbyBoards(unittest.TestCase):
    def test_returns_defaults_when_fetch_fails(self) -> None:
        with patch(
            "jobforager.company_lists._fetch_json",
            side_effect=IOError("network down"),
        ), patch(
            "jobforager.company_lists._load_local_json",
            return_value=None,
        ):
            boards = get_ashby_boards()
        self.assertIsInstance(boards, list)
        self.assertIn("supabase", boards)

    def test_returns_merged_defaults_and_fetched(self) -> None:
        with patch(
            "jobforager.company_lists._fetch_json",
            return_value=["ramp", "linear"],
        ), patch(
            "jobforager.company_lists._load_local_json",
            return_value=None,
        ), patch(
            "jobforager.company_lists._save_local_json",
        ) as mock_save:
            boards = get_ashby_boards()
        expected = sorted(
            set(
                ["supabase", "ramp", "figma", "linear", "vercel", "openai", "clearbank"]
                + ["ramp", "linear"]
            )
        )
        self.assertEqual(boards, expected)
        mock_save.assert_called_once()


class TestGetSmartrecruitersSlugs(unittest.TestCase):
    def test_returns_defaults_when_fetch_fails(self) -> None:
        with patch(
            "jobforager.company_lists._load_csv_slugs",
            return_value=None,
        ), patch(
            "jobforager.company_lists._load_local_json",
            return_value=None,
        ):
            slugs = get_smartrecruiters_slugs()
        self.assertIsInstance(slugs, list)
        self.assertIn("adobe1", slugs)

    def test_returns_merged_defaults_and_fetched(self) -> None:
        with patch(
            "jobforager.company_lists._load_csv_slugs",
            return_value=["canva", "deloitte6"],
        ), patch(
            "jobforager.company_lists._load_local_json",
            return_value=None,
        ), patch(
            "jobforager.company_lists._save_local_json",
        ) as mock_save:
            slugs = get_smartrecruiters_slugs()
        expected = sorted(
            set(
                ["adobe1", "canva", "deloitte6", "experian", "samsung1", "wise"]
                + ["canva", "deloitte6"]
            )
        )
        self.assertEqual(slugs, expected)
        mock_save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
