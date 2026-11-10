"""Regression for actual HTTP login lockout and independent accounts."""
from scripts.audit_login_lockout_http_b10921 import run


def test_login_lockout_http_b10921():
    result = run()
    assert result['status'] == 'PASS'
    assert result['passed'] == 13
    assert result['postgresql_tested'] is False
