"""Contract checks against the ACTUAL existing wallet preview.

The PayU preparation helpers must not silently diverge from the wallet's
frozen withdrawal quote or its deliberately simulated topup boundary.
"""
import pytest
from backend.wallet_preview import withdrawal_terms, enabled, validate_environment
from backend.payu_preparation import (
    seller_withdrawal_split, customer_withdrawal_split,
    PayUDisabledAdapter, PayUNotConfigured, PaymentRequest,
)


@pytest.mark.parametrize("amount", [1, 2, 3, 9, 10, 11, 19, 20, 21, 99, 100, 101,
                                   199, 200, 201, 999, 1000, 1001, 10001, 1000000,
                                   100000000])
@pytest.mark.parametrize("role", ["klient", "rolnik"])
def test_payout_quote_matches_existing_wallet(amount, role):
    quote = withdrawal_terms(amount, role)
    net, fee = (seller_withdrawal_split(amount) if role == "rolnik"
                else customer_withdrawal_split(amount))
    assert (quote["net_grosze"], quote["fee_grosze"]) == (net, fee)
    assert quote["gross_grosze"] == net + fee
    assert quote["fee_basis_points"] == (500 if role == "rolnik" else 0)


def test_wallet_preview_cannot_be_enabled_in_production():
    assert not enabled({"WP_ENV": "production"})
    with pytest.raises(ValueError):
        validate_environment({"WP_ENV": "production", "WP_ENABLE_WALLET_PREVIEW": "1"})


def test_payment_adapter_stays_disabled_even_for_valid_wallet_amount():
    adapter = PayUDisabledAdapter()
    with pytest.raises(PayUNotConfigured):
        adapter.create_topup(PaymentRequest("integration-test", 1, 100))
