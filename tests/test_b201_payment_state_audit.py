from dataclasses import replace
import pytest
from backend.payment_simulator import new_payment, apply_event
from backend.payment_state_audit import audit_payment

@pytest.mark.parametrize('products,delivery', [(1,0),(99,1),(10000,999),(123456789,0)])
def test_valid_lifecycle(products, delivery):
    p = new_payment(1,products,delivery)
    assert audit_payment(p).valid
    p = apply_event(p,'a','payment_success_test')
    assert audit_payment(p).valid
    refunded = apply_event(p,'b','delivery_failed_by_courier_test')
    assert audit_payment(refunded).valid
    assert refunded.refund_grosze == products + delivery
    completed = apply_event(p,'c','order_completed_test')
    assert audit_payment(completed).valid
    paid_out = apply_event(completed,'d','weekly_payout_test')
    assert audit_payment(paid_out).valid

@pytest.mark.parametrize('field,value,issue', [
    ('total_grosze',999,'total_mismatch'),
    ('seller_grosze',999,'allocation_mismatch'),
    ('refund_grosze',1,'state_amount_mismatch'),
    ('payout_grosze',1,'state_amount_mismatch'),
    ('state','made_up','unknown_state'),
    ('order_id',0,'negative_amount_or_invalid_id'),
    ('total_grosze',1.0,'non_integer_amount_or_id'),
    ('processed_event_ids',frozenset({''}),'invalid_event_ids'),
])
def test_corruption_detected(field,value,issue):
    p = replace(new_payment(1,100,0), **{field:value})
    assert issue in audit_payment(p).issues

def test_idempotency():
    p = apply_event(new_payment(1,100,0),'same','payment_success_test')
    assert apply_event(p,'same','payment_success_test') == p

def test_no_double_refund():
    p = apply_event(new_payment(1,100,0),'a','payment_success_test')
    p = apply_event(p,'b','delivery_failed_by_courier_test')
    with pytest.raises(ValueError):
        apply_event(p,'c','delivery_failed_by_courier_test')
