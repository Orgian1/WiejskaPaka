"""Regression: CLI must define database probe before calling main()."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_module_entrypoint_rejects_missing_environment_without_nameerror():
    env = {k: v for k, v in os.environ.items() if k not in {
        'WP_ENV', 'WP_TEST_DATABASE_URL', 'DATABASE_URL', 'WIEJSKAPAKA_DB',
        'WP_REAL_PAYMENTS', 'WP_PSP_SECRET', 'STRIPE_SECRET_KEY',
    }}
    env['WP_ENV'] = 'test'
    result = subprocess.run([sys.executable, '-m', 'backend.test_server_launcher'],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert 'Dedicated test PostgreSQL URL is required' in result.stderr
    assert 'NameError' not in result.stderr


def test_probe_defined_before_cli_invocation():
    source = (ROOT / 'backend' / 'test_server_launcher.py').read_text()
    assert source.index('def verify_test_database_connection(') < source.index("if __name__ == '__main__':")
