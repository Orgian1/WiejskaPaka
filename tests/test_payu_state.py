import pytest

from backend.payu_preparation import PaymentStatus as S
from backend.payu_state import payment_transition


@pytest.mark.parametrize("before,after", [
    (S.CREATED,S.PENDING), (S.CREATED,S.CONFIRMED),
    (S.PENDING,S.CONFIRMED), (S.PENDING,S.FAILED),
    (S.CONFIRMED,S.REFUNDED),
])
def test_allowed_payment_transitions(before, after):
    assert payment_transition(before, after) is True


@pytest.mark.parametrize("before,after", [
    (S.CONFIRMED,S.FAILED), (S.CONFIRMED,S.CANCELLED),
    (S.FAILED,S.CONFIRMED), (S.CANCELLED,S.CONFIRMED),
    (S.REFUNDED,S.CONFIRMED), (S.PENDING,S.CREATED),
])
def test_invalid_out_of_order_payment_transitions(before, after):
    with pytest.raises(ValueError):
        payment_transition(before, after)


def test_duplicate_webhook_state_is_noop():
    assert payment_transition(S.CONFIRMED,S.CONFIRMED) is False


def test_untyped_callback_cannot_be_used_as_verified_state():
    with pytest.raises(ValueError):
        payment_transition(S.PENDING, "CONFIRMED")
