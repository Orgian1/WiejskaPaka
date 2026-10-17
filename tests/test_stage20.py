import pytest
from backend.payment_simulator import new_payment, apply_event


def test_full_refund_includes_delivery():
    p = new_payment(1, 9999, 1200)
    p = apply_event(p, 'payment-1', 'payment_success_test')
    p = apply_event(p, 'courier-1', 'delivery_failed_by_courier_test')
    assert p.refund_grosze == 11199 and p.payout_grosze == 0
    assert p.state == 'refunded_test'


def test_weekly_payout_after_completion_only():
    p = new_payment(1, 9999, 1200)
    with pytest.raises(ValueError):
        apply_event(p, 'early', 'weekly_payout_test')
    p = apply_event(p, 'paid', 'payment_success_test')
    p = apply_event(p, 'completed', 'order_completed_test')
    p = apply_event(p, 'weekly', 'weekly_payout_test')
    assert p.payout_grosze == 10699
    assert p.commission_grosze + p.payout_grosze == p.total_grosze


def test_idempotency_and_no_double_refund():
    p = apply_event(new_payment(1, 100, 10), 'p', 'payment_success_test')
    p = apply_event(p, 'r', 'delivery_failed_by_courier_test')
    assert apply_event(p, 'r', 'delivery_failed_by_courier_test') == p
    with pytest.raises(ValueError):
        apply_event(p, 'r2', 'delivery_failed_by_courier_test')


def test_failed_payment_cannot_payout():
    p = apply_event(new_payment(1, 100, 0), 'f', 'payment_failed_test')
    with pytest.raises(ValueError):
        apply_event(p, 'x', 'weekly_payout_test')

@pytest.mark.parametrize('bad', [0, -1, True, 1.2])
def test_invalid_order_id(bad):
    with pytest.raises(ValueError):
        new_payment(bad, 100, 0)
