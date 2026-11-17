import pytest

from backend.payu_config import PayUEnvironment, load_payu_settings


def test_payu_disabled_by_default():
    settings = load_payu_settings({})
    assert settings.environment == PayUEnvironment.DISABLED
    assert not settings.enabled


def test_payu_sandbox_requires_credentials():
    with pytest.raises(ValueError):
        load_payu_settings({"WP_PAYU_MODE": "sandbox"})
    settings = load_payu_settings({
        "WP_PAYU_MODE": "sandbox", "WP_PAYU_CLIENT_ID": "id",
        "WP_PAYU_CLIENT_SECRET": "very-secret",
        "WP_PAYU_POS_ID": "pos", "WP_PAYU_SECOND_KEY": "key",
    })
    assert settings.enabled
    assert "very-secret" not in repr(settings)


def test_payu_production_is_explicitly_blocked():
    with pytest.raises(ValueError):
        load_payu_settings({"WP_PAYU_MODE": "production"})


def test_invalid_payu_mode_is_rejected():
    with pytest.raises(ValueError):
        load_payu_settings({"WP_PAYU_MODE": "anything"})
