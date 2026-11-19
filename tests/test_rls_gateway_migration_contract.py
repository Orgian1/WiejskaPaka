"""Static checks for staged gateway migration; never executes SQL."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
UP = ROOT / 'database/security_rls/001_gateway.up.sql'
DOWN = ROOT / 'database/security_rls/001_gateway.down.sql'


class GatewayMigrationContract(unittest.TestCase):
    def test_migration_files_are_present_and_nonempty(self):
        self.assertTrue(UP.is_file())
        self.assertTrue(DOWN.is_file())
        self.assertGreater(UP.stat().st_size, 1000)
        self.assertGreater(DOWN.stat().st_size, 100)

    def test_gateway_api_is_declared(self):
        sql = UP.read_text(encoding='utf-8').lower()
        self.assertIn('wp_rls', sql)
        self.assertIn('execute', sql)
        self.assertIn('describe', sql)

    def test_no_automatic_migration_in_test(self):
        self.assertNotIn('subprocess', Path(__file__).read_text(encoding='utf-8'))
        self.assertNotIn('psycopg.connect', Path(__file__).read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
