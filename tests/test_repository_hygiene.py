from pathlib import PurePosixPath
import unittest

from scripts.check_repository_hygiene import violation_reason


class RepositoryHygieneTests(unittest.TestCase):
    def test_allows_public_repository_files(self):
        for path in (
            "examples/sample-job.json",
            ".env.example",
            "src/cli.py",
        ):
            with self.subTest(path=path):
                self.assertIsNone(violation_reason(PurePosixPath(path)))

    def test_rejects_local_data_directories(self):
        for path in (
            "applications/current.json",
            "data/export.json",
            "resumes/example.txt",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    violation_reason(PurePosixPath(path)),
                    "local-data or generated directory",
                )

    def test_rejects_environment_and_credential_files(self):
        expected = {
            ".env": "environment file",
            ".env.local": "environment file",
            "private.pem": "sensitive or local-data file type",
            "id_ed25519": "local or credential filename",
        }
        for path, reason in expected.items():
            with self.subTest(path=path):
                self.assertEqual(violation_reason(PurePosixPath(path)), reason)

    def test_rejects_local_data_file_types(self):
        for path in ("jobs.csv", "notes.log", "cache.sqlite3"):
            with self.subTest(path=path):
                self.assertEqual(
                    violation_reason(PurePosixPath(path)),
                    "sensitive or local-data file type",
                )


if __name__ == "__main__":
    unittest.main()
