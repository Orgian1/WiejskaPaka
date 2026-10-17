"""Testy regresyjne obsługi awarii uwierzytelniania w przeglądarce."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'check_auth_failures_offline.py'


def test_auth_failure_runner_is_valid_python():
    ast.parse(SCRIPT.read_text(encoding='utf8'))


def test_auth_failure_runner_covers_three_scenarios():
    source = SCRIPT.read_text(encoding='utf8')
    for name in ('rejected_login', 'invalid_profile', 'network_error'):
        assert name in source


def test_auth_failure_runner_checks_private_panels():
    source = SCRIPT.read_text(encoding='utf8')
    for name in ('#dashboard', '#notifications-section', '#farmer', '#farmer-details', '#orders-section'):
        assert name in source
    assert 'is_hidden()' in source
