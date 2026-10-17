"""Regression contract for the cross-account HTTP privacy audit."""
from pathlib import Path


def test_cross_account_audit_checks_phone_field_privacy():
    script = (Path(__file__).resolve().parents[1] / 'scripts' / 'audit_cross_account_http.py').read_text(encoding='utf-8')
    assert 'assert_no_phone_fields' in script
    for field in ('phone_number', 'telephone', 'mobile', 'telefon', 'numer_telefonu'):
        assert field in script
    assert "('public catalog', '/products', None)" in script
    assert "('buyer orders', '/orders/me', 'buyer')" in script
    assert "('farmer events', f'/orders/{oid}/events', 'farmer')" in script
