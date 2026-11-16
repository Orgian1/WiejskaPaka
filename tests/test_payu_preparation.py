import pytest

from backend.payu_preparation import (
    PaymentRequest, PaymentStatus, PayUDisabledAdapter, PayUNotConfigured,
    SimulatedPaymentProvider, seller_withdrawal_split, customer_withdrawal_split,
)


def test_payment_request_rejects_invalid_money():
    for amount in (0, -1, 0.5, 1.0, True, "100"):
        with pytest.raises(ValueError):
            PaymentRequest("order-1", 1, amount)
    assert PaymentRequest("order-1", 1, 101).amount_grosze == 101


def test_disabled_payu_cannot_initiate_payment():
    with pytest.raises(PayUNotConfigured):
        PayUDisabledAdapter().create_topup(PaymentRequest("order-1", 1, 100))


def test_simulated_topup_idempotent_and_terminal():
    provider = SimulatedPaymentProvider()
    request = PaymentRequest("order-1", 1, 100)
    first = provider.create_topup(request)
    assert provider.create_topup(request) == first
    assert provider.get_payment_status(first.provider_order_id) == PaymentStatus.PENDING
    provider.set_test_status("order-1", PaymentStatus.CONFIRMED)
    assert provider.get_payment_status(first.provider_order_id) == PaymentStatus.CONFIRMED
    with pytest.raises(ValueError):
        provider.set_test_status("order-1", PaymentStatus.FAILED)


def test_simulated_refund_requires_confirmation():
    provider = SimulatedPaymentProvider()
    payment = provider.create_topup(PaymentRequest("order-2", 2, 200))
    with pytest.raises(ValueError):
        provider.request_refund(payment.provider_order_id, 200, "refund-1")
    provider.set_test_status("order-2", PaymentStatus.CONFIRMED)
    assert provider.request_refund(payment.provider_order_id, 200, "refund-1") == "refund-1"
    assert provider.request_refund(payment.provider_order_id, 200, "refund-1") == "refund-1"


@pytest.mark.parametrize("amount", [1, 9, 10, 11, 99, 100, 101, 999, 10000, 99999999])
def test_seller_commission_preserves_every_grosz(amount):
    net, fee = seller_withdrawal_split(amount)
    assert net + fee == amount
    assert fee == (amount * 5 + 50) // 100
    assert customer_withdrawal_split(amount) == (amount, 0)


def test_simulated_operation_id_cannot_change_amount():
    provider = SimulatedPaymentProvider()
    provider.create_topup(PaymentRequest("same", 1, 100))
    with pytest.raises(ValueError):
        provider.create_topup(PaymentRequest("same", 1, 200))


def test_simulated_refunds_never_exceed_original_payment():
    provider = SimulatedPaymentProvider()
    payment = provider.create_topup(PaymentRequest("payment", 1, 100))
    provider.set_test_status("payment", PaymentStatus.CONFIRMED)
    assert provider.request_refund(payment.provider_order_id, 40, "first") == "first"
    assert provider.request_refund(payment.provider_order_id, 60, "second") == "second"
    with pytest.raises(ValueError):
        provider.request_refund(payment.provider_order_id, 1, "third")
    with pytest.raises(ValueError):
        provider.request_refund(payment.provider_order_id, 41, "first")
