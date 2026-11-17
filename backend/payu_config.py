"""Strict runtime configuration gate for future PayU integration.

This does not authenticate with PayU. Credentials are never committed to source.
Live payouts remain blocked until a separately approved contract and provider
integration is implemented and tested.
"""
from dataclasses import dataclass
from enum import Enum
import os


class PayUEnvironment(str, Enum):
    DISABLED = "disabled"
    SANDBOX = "sandbox"
    PRODUCTION = "production"


@dataclass(frozen=True)
class PayUSettings:
    environment: PayUEnvironment
    client_id: str | None
    client_secret: str | None
    merchant_pos_id: str | None
    second_key: str | None

    @property
    def enabled(self) -> bool:
        return self.environment != PayUEnvironment.DISABLED

    def __repr__(self):
        return f"PayUSettings(environment={self.environment.value!r}, credentials='[REDACTED]')"


def load_payu_settings(environ=None) -> PayUSettings:
    env = os.environ if environ is None else environ
    mode = env.get("WP_PAYU_MODE", "disabled").strip().lower()
    if mode not in ("disabled", "sandbox", "production"):
        raise ValueError("WP_PAYU_MODE must be disabled, sandbox, or production")
    environment = PayUEnvironment(mode)
    keys = ("WP_PAYU_CLIENT_ID", "WP_PAYU_CLIENT_SECRET",
            "WP_PAYU_POS_ID", "WP_PAYU_SECOND_KEY")
    values = [env.get(key) or None for key in keys]
    if environment == PayUEnvironment.PRODUCTION:
        raise ValueError("PayU production remains disabled pending explicit rollout approval")
    if environment == PayUEnvironment.SANDBOX and any(not value or not value.strip() for value in values):
        raise ValueError("PayU sandbox requires all credentials")
    return PayUSettings(environment, *values)
