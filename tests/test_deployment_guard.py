import pytest
from backend.deployment_guard import assert_safe_environment

@pytest.mark.parametrize('value', ['production', 'PROD', ' live '])
def test_production_blocked(value):
    with pytest.raises(RuntimeError, match='zablokowane'):
        assert_safe_environment({'WP_ENV': value})

@pytest.mark.parametrize('value', ['development', 'test', 'DEV'])
def test_development_allowed(value):
    assert assert_safe_environment({'WP_ENV': value}) in ('development', 'test', 'dev')

def test_unknown_mode_blocked():
    with pytest.raises(RuntimeError, match='nieznany'):
        assert_safe_environment({'WP_ENV': 'staging-unsafe'})

def test_default_development():
    assert assert_safe_environment({}) == 'development'
