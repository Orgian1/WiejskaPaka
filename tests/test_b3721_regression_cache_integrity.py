"""Ensure cached green tests are invalidated after changes to runtime code."""
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_tests_per_file import application_fingerprint


class RegressionFingerprintTests(unittest.TestCase):
    def test_changes_in_application_invalidate_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'backend').mkdir()
            (root / 'backend' / 'app.py').write_text('a=1')
            first = application_fingerprint(root)
            (root / 'backend' / 'app.py').write_text('a=2')
            self.assertNotEqual(first, application_fingerprint(root))

    def test_ignores_generated_sqlite_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'backend').mkdir()
            first = application_fingerprint(root)
            (root / 'backend' / 'test.sqlite3').write_text('temporary')
            self.assertEqual(first, application_fingerprint(root))

    def test_dependency_changes_invalidate_cached_test_evidence(self):
        for name in ('requirements.txt','requirements-lock.txt'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);path=root/name
                path.write_text('cryptography==49.0.0\n');old=application_fingerprint(root)
                path.write_text('cryptography==50.0.2\n')
                self.assertNotEqual(old,application_fingerprint(root))
