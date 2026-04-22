import unittest

from jobforager.normalize.recruiter_detector import is_recruiter_company
from jobforager.search import (
    filter_by_excluded_keywords,
    filter_by_experience_level,
    filter_by_recruiter,
)
from jobforager.models import JobRecord


class TestFilterByExcludedKeywords(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            JobRecord(
                source="test",
                title="Senior Python Developer",
                company="TechCorp",
                job_url="https://example.com/1",
                tags=["python", "django"],
            ),
            JobRecord(
                source="test",
                title="Junior Frontend Engineer",
                company="StartupX",
                job_url="https://example.com/2",
                tags=["react", "javascript"],
            ),
            JobRecord(
                source="test",
                title="Staffing Coordinator",
                company="Global Staffing Solutions",
                job_url="https://example.com/3",
                description="We are a staffing agency",
            ),
        ]

    def test_excludes_by_title(self) -> None:
        result = filter_by_excluded_keywords(self.records, ["senior"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].title, "Junior Frontend Engineer")
        self.assertEqual(result[1].title, "Staffing Coordinator")

    def test_excludes_by_company(self) -> None:
        result = filter_by_excluded_keywords(self.records, ["staffing"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].title, "Senior Python Developer")
        self.assertEqual(result[1].title, "Junior Frontend Engineer")

    def test_excludes_by_description(self) -> None:
        result = filter_by_excluded_keywords(self.records, ["agency"])
        self.assertEqual(len(result), 2)

    def test_excludes_by_tags(self) -> None:
        result = filter_by_excluded_keywords(self.records, ["react"])
        self.assertEqual(len(result), 2)

    def test_multiple_excluded(self) -> None:
        result = filter_by_excluded_keywords(self.records, ["senior", "junior"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Staffing Coordinator")

    def test_none_excluded(self) -> None:
        result = filter_by_excluded_keywords(self.records, None)
        self.assertEqual(len(result), 3)

    def test_empty_excluded(self) -> None:
        result = filter_by_excluded_keywords(self.records, [])
        self.assertEqual(len(result), 3)


class TestFilterByExperienceLevel(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            JobRecord(
                source="test",
                title="Software Engineering Intern",
                company="TechCorp",
                job_url="https://example.com/1",
            ),
            JobRecord(
                source="test",
                title="Junior Frontend Engineer",
                company="StartupX",
                job_url="https://example.com/2",
            ),
            JobRecord(
                source="test",
                title="Software Engineer",
                company="BigCorp",
                job_url="https://example.com/3",
            ),
            JobRecord(
                source="test",
                title="Senior Backend Developer",
                company="ScaleUp",
                job_url="https://example.com/4",
            ),
        ]

    def test_filter_intern(self) -> None:
        result = filter_by_experience_level(self.records, "intern")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Software Engineering Intern")

    def test_filter_entry(self) -> None:
        result = filter_by_experience_level(self.records, "entry")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Junior Frontend Engineer")

    def test_filter_mid(self) -> None:
        result = filter_by_experience_level(self.records, "mid")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Software Engineer")

    def test_filter_senior(self) -> None:
        result = filter_by_experience_level(self.records, "senior")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Senior Backend Developer")

    def test_none_level(self) -> None:
        result = filter_by_experience_level(self.records, None)
        self.assertEqual(len(result), 4)

    def test_invalid_level(self) -> None:
        result = filter_by_experience_level(self.records, "invalid")
        self.assertEqual(len(result), 4)


class TestFilterByRecruiter(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            JobRecord(
                source="test",
                title="Python Developer",
                company="TechCorp",
                job_url="https://example.com/1",
            ),
            JobRecord(
                source="test",
                title="Frontend Engineer",
                company="Global Staffing Solutions",
                job_url="https://example.com/2",
            ),
            JobRecord(
                source="test",
                title="Data Scientist",
                company="TalentHub Recruiting",
                job_url="https://example.com/3",
            ),
        ]

    def test_hide_recruiters(self) -> None:
        result = filter_by_recruiter(self.records, True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].company, "TechCorp")

    def test_show_recruiters(self) -> None:
        result = filter_by_recruiter(self.records, False)
        self.assertEqual(len(result), 3)


class TestIsRecruiterCompany(unittest.TestCase):
    def test_recruiter_names(self) -> None:
        self.assertTrue(is_recruiter_company("Acme Staffing"))
        self.assertTrue(is_recruiter_company("Tech Talent Solutions"))
        self.assertTrue(is_recruiter_company("Global Recruiting Agency"))
        self.assertTrue(is_recruiter_company("DevSearch Placement"))

    def test_non_recruiter_names(self) -> None:
        self.assertFalse(is_recruiter_company("Google"))
        self.assertFalse(is_recruiter_company("Stripe"))
        self.assertFalse(is_recruiter_company("StartupXYZ"))


if __name__ == "__main__":
    unittest.main()
