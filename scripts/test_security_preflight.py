import unittest

from scripts.security_preflight import is_sensitive


class SecurityPreflightTests(unittest.TestCase):
    def test_sensitive_runtime_files_are_rejected(self):
        for path in (
            ".env",
            "db.sqlite3",
            "data/local.sqlite3",
            "deployment/private.key",
            "backups/production.dump",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_sensitive(path))

    def test_safe_repository_files_are_allowed(self):
        for path in (
            ".env.example",
            "finance/models.py",
            "deployment/nginx.conf",
        ):
            with self.subTest(path=path):
                self.assertFalse(is_sensitive(path))


if __name__ == "__main__":
    unittest.main()
