import unittest

from jobforager.normalize.experience_level import extract_experience_level


class TestExtractExperienceLevel(unittest.TestCase):
    def test_intern(self) -> None:
        self.assertEqual(extract_experience_level("Software Engineering Intern"), "intern")
        self.assertEqual(extract_experience_level("Data Science Internship"), "intern")
        self.assertEqual(extract_experience_level("Summer Intern - Backend"), "intern")

    def test_entry(self) -> None:
        self.assertEqual(extract_experience_level("Junior Software Engineer"), "entry")
        self.assertEqual(extract_experience_level("Entry Level Data Analyst"), "entry")
        self.assertEqual(extract_experience_level("Graduate Trainee Developer"), "entry")

    def test_mid(self) -> None:
        self.assertEqual(extract_experience_level("Software Engineer"), "mid")
        self.assertEqual(extract_experience_level("Backend Developer"), "mid")
        self.assertEqual(extract_experience_level("Product Manager"), "mid")

    def test_senior(self) -> None:
        self.assertEqual(extract_experience_level("Senior Software Engineer"), "senior")
        self.assertEqual(extract_experience_level("Staff Engineer"), "senior")
        self.assertEqual(extract_experience_level("Principal Data Scientist"), "senior")
        self.assertEqual(extract_experience_level("Director of Engineering"), "senior")
        self.assertEqual(extract_experience_level("VP of Product"), "senior")

    def test_empty(self) -> None:
        self.assertEqual(extract_experience_level(""), "unknown")


if __name__ == "__main__":
    unittest.main()
