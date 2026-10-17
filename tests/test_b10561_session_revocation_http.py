"""Live local HTTP security regression for multiple session revocation."""
from scripts.audit_session_revocation_http import run


def test_independent_session_revocation_over_http():
    result = run()
    assert result['status'] == 'PASS'
    assert result['passed'] >= 35
    assert any('survives buyer logout all' in check for check in result['checks'])
    assert any('fresh token works' in check for check in result['checks'])
