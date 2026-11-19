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

    def test_activation_requires_explicit_compatibility_approval(self):
        sql = UP.read_text(encoding='utf-8')
        self.assertIn("wp_rls.api_compatibility_verified", sql)
        self.assertIn("RLS activation blocked", sql)
        self.assertIn("wp_rls.disposable_test", sql)
        self.assertIn("current_database()", sql)

    def test_sensitive_role_permissions_are_restricted(self):
        sql = UP.read_text(encoding='utf-8')
        self.assertIn("NOBYPASSRLS", sql)
        self.assertIn("NOSUPERUSER", sql)
        self.assertIn("REVOKE ALL ON SCHEMA wp_rls FROM PUBLIC", sql)
        self.assertIn("REVOKE ALL ON SCHEMA wp_rls_keys FROM PUBLIC", sql)

    def test_no_automatic_migration_in_application_startup(self):
        app = (ROOT / 'backend/app.py').read_text(encoding='utf-8')
        self.assertNotIn('security_rls/001_gateway.up.sql', app)
        self.assertNotIn('wp_rls.api_compatibility_verified', app)


if __name__ == '__main__':
    unittest.main()
