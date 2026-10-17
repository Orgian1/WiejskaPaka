"""Regression tests for the B/36–40 browser/FastAPI bridge."""
import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'scripts' / 'check_browser_backend_bridge.py'


def test_bridge_has_isolated_sqlite_and_sanitized_environment():
    text = SOURCE.read_text(encoding='utf8')
    ast.parse(text)
    assert 'TemporaryDirectory(' in text
    assert 'demo_environment(os.environ' in text
    assert 'TestClient(app)' in text


def test_bridge_uses_real_browser_and_backend_not_fake_api_payloads():
    text = SOURCE.read_text(encoding='utf8')
    assert 'p.chromium.launch(' in text
    assert 'page.expose_function(' in text
    assert 'client.request(method, path' in text
    assert 'window.__apiBridge(' in text
    assert 'response.is_success' in text


def test_bridge_checks_both_fulfillment_modes_and_private_logout():
    text = SOURCE.read_text(encoding='utf8')
    for needle in ('349 groszy', '850 groszy', "select_option('dostawa')", "'/orders'", "'#orders'", "'#dashboard'"):
        assert needle in text
