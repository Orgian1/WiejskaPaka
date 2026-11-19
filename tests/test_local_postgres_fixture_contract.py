"""Safety checks for the optional isolated PostgreSQL fixture."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LocalPostgresFixtureContract(unittest.TestCase):
    def test_fixture_never_uses_external_dsn(self):
        code = (ROOT / 'tests/local_postgres.py').read_text(encoding='utf-8')
        self.assertIn("127.0.0.1", code)
        self.assertIn("directory.exists()", code)
        self.assertIn("pgserver.initdb", code)
        self.assertNotIn("DATABASE_URL", code)
        self.assertNotIn("WP_TEST_POSTGRES_DSN", code)

    def test_optional_test_dependencies_are_separate(self):
        content = (ROOT / 'requirements-security-test.txt').read_text(encoding='utf-8')
        self.assertIn('pgserver==', content)
        self.assertIn('requirements-lock.txt', content)


if __name__ == '__main__':
    unittest.main()
