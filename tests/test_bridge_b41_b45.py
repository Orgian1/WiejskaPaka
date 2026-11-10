"""Checks the integration runner retains B/41-B/45 safety scenarios."""
import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'scripts' / 'check_browser_backend_bridge.py'


def test_extended_bridge_is_valid_python_and_checks_stock():
    code = SOURCE.read_text(encoding='utf8')
    ast.parse(code)
    assert 'stock_after_cancel == 2' in code
    assert 'repeat.status_code == 409' in code
    assert 'invalid.status_code in (409, 422)' in code


def test_extended_bridge_checks_pin_security_and_roles():
    code = SOURCE.read_text(encoding='utf8')
    assert "login('rolnik')" in code
    assert 'pozostało prób: 4' in code
    assert 'reused.status_code == 409' in code
    assert "get_by_role('checkbox').check()" in code
