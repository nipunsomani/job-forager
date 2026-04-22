from __future__ import annotations

from pathlib import Path
import textwrap
import unittest
import uuid

from jobforager.config import load_candidate_profile
from jobforager.models import CandidateProfile


class TestProfileLoader(unittest.TestCase):
    def _write_profile(self, content: str) -> Path:
        tests_root = Path(__file__).resolve().parents[1] / "tests"
        path = tests_root / f"profile_loader_tmp_{uuid.uuid4().hex}.toml"
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
        return path

    def test_profile_loader_supports_aliases(self) -> None:
        profile_path = self._write_profile(
            """
            [profile]
            location = "London, UK"

            [targets]
            titles = ["Platform Engineer"]
            skills = ["python"]

            [preferences]
            remotepreference = "remoteonly"
            minbasesalary_usd = 120000
            """
        )

        profile = load_candidate_profile(profile_path)
        self.assertEqual(profile.remote_preference, "remote_only")
        self.assertEqual(profile.salary_floor_usd, 120000)
        self.assertEqual(profile.locations, ["London, UK"])

    def test_invalid_remote_preference_raises_value_error(self) -> None:
        profile_path = self._write_profile(
            """
            [targets]
            titles = ["Platform Engineer"]
            skills = ["python"]

            [preferences]
            remote_preference = "satellite_mode"
            """
        )

        with self.assertRaisesRegex(ValueError, "Invalid remote_preference value"):
            load_candidate_profile(profile_path)

    def test_source_toggles_parsed_from_sources_section(self) -> None:
        profile_path = self._write_profile(
            """
            [targets]
            titles = ["Platform Engineer"]
            skills = ["python"]

            [sources]
            enable_sample = true
            enable_file = false
            enable_remotive = true
            enable_linkedin = "yes"
            """
        )

        profile = load_candidate_profile(profile_path)
        self.assertEqual(profile.source_toggles.get("sample"), True)
        self.assertEqual(profile.source_toggles.get("file"), False)
        self.assertEqual(profile.source_toggles.get("remotive"), True)
        self.assertEqual(profile.source_toggles.get("linkedin"), True)

    def test_negative_salary_floor_in_toml_raises_value_error(self) -> None:
        profile_path = self._write_profile(
            """
            [targets]
            titles = ["Platform Engineer"]
            skills = ["python"]

            [preferences]
            salary_floor_usd = -50000
            """
        )

        with self.assertRaisesRegex(ValueError, "at least 0"):
            load_candidate_profile(profile_path)

    def test_direct_candidate_profile_invalid_salary_floor_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "salary_floor_usd must be non-negative"):
            CandidateProfile(salary_floor_usd=-1)

    def test_direct_candidate_profile_invalid_remote_preference_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "remote_preference must be one of"):
            CandidateProfile(remote_preference="orbital")

    def test_direct_candidate_profile_invalid_source_toggles_raises(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "source_toggles must be a dict with string keys and boolean values"
        ):
            CandidateProfile(source_toggles={"sample": "yes"})


if __name__ == "__main__":
    unittest.main()
