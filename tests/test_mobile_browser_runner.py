"""Bezpieczny runner prawdziwej przeglądarki nie dotyka Neon."""
from pathlib import Path
import ast
from scripts.check_mobile_browser import find_chromium, free_port
from scripts.run_phone_demo import demo_environment


def test_browser_runner_uses_localhost_and_disposable_database():
    source = Path(__file__).resolve().parents[1] / 'scripts' / 'check_mobile_browser.py'
    content = source.read_text(encoding='utf-8')
    ast.parse(content)
    assert "'127.0.0.1'" in content
    assert 'TemporaryDirectory(' in content
    assert 'demo_environment(os.environ' in content
    assert 'process.terminate()' in content
    assert 'document.documentElement.scrollWidth' in content


def test_demo_environment_excludes_external_database_credentials():
    env = demo_environment({'DATABASE_URL': 'postgresql://fake.invalid/live',
                            'WP_TEST_DATABASE_URL': 'postgresql://fake.invalid/test',
                            'WIEJSKAPAKA_ENV': 'production'}, Path('/tmp/demo-only.sqlite3'))
    assert 'DATABASE_URL' not in env
    assert 'WP_TEST_DATABASE_URL' not in env
    assert env['WIEJSKAPAKA_ENV'] == 'development'
    assert env['WIEJSKAPAKA_DB'].endswith('demo-only.sqlite3')


def test_browser_runner_can_allocate_local_port():
    assert 0 < free_port() < 65536
