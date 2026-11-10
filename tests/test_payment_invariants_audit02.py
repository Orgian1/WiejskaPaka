"""Regression checks: payment simulations must never accept corrupted grosze."""
from dataclasses import replace
import pytest
from backend.payment_simulator import apply_event, new_payment
from backend.money import split_75_20_5

@pytest.mark.parametrize('amount', range(0, 1001))
def test_split_conserves_every_grosz(amount):
    parts = split_75_20_5(amount)
    assert sum(parts) == amount
    assert all(type(x) is int and x >= 0 for x in parts)

@pytest.mark.parametrize('field,value', [
    ('total_grosze', 1), ('products_grosze', -1),
    ('delivery_grosze', True), ('commission_grosze', 99999),
    ('seller_grosze', 0), ('refund_grosze', 99999),
    ('payout_grosze', 99999),
])
def test_reject_corrupt_financial_state_even_for_duplicate_event(field, value):
    p = new_payment(1, 1000, 125)
    p = apply_event(p, 'paid-1', 'payment_success_test')
    p = replace(p, **{field: value})
    with pytest.raises(ValueError):
        apply_event(p, 'paid-1', 'payment_success_test')

def test_courier_failure_returns_exact_full_total_and_never_pays_out():
    for products in (1, 2, 3, 99, 100, 101, 9999):
        for delivery in (0, 1, 99, 100):
            p = new_payment(1, products, delivery)
            p = apply_event(p, 'paid', 'payment_success_test')
            p = apply_event(p, 'courier-failed', 'delivery_failed_by_courier_test')
            assert p.refund_grosze == products + delivery
            assert p.payout_grosze == 0
            with pytest.raises(ValueError):
                apply_event(p, 'payout', 'weekly_payout_test')
