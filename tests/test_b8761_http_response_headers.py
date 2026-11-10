"""Regression: all tested HTTP response classes keep security headers."""
from scripts.audit_http_response_headers import run


def test_security_headers_for_success_and_errors():
    result = run()
    assert result['status'] == 'PASS'
    assert result['count'] >= 13
    assert {item['status'] for item in result['checks']} >= {200, 201, 401, 403, 404, 422}
