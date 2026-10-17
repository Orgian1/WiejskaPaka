"""Offline payment/refund state machine. No PSP, bank or external API calls."""
from dataclasses import dataclass, replace
from backend.settlement_preview import calculate

@dataclass(frozen=True)
class PaymentSimulation:
    order_id: int
    total_grosze: int
    products_grosze: int
    delivery_grosze: int
    commission_grosze: int
    seller_grosze: int
    state: str = 'awaiting_payment'
    refund_grosze: int = 0
    payout_grosze: int = 0
    processed_event_ids: frozenset[str] = frozenset()


def new_payment(order_id: int, products_grosze: int, delivery_grosze: int, commission_basis_points: int = 500) -> PaymentSimulation:
    if type(order_id) is not int or order_id <= 0:
        raise ValueError('Nieprawidłowe zamówienie')
    values = calculate(products_grosze, delivery_grosze, commission_basis_points)
    if values['customer_total_grosze'] <= 0:
        raise ValueError('Płatność musi być dodatnia')
    return PaymentSimulation(order_id, values['customer_total_grosze'], products_grosze, delivery_grosze,
                             values['commission_grosze'], values['seller_amount_grosze'])


def apply_event(payment: PaymentSimulation, event_id: str, event: str) -> PaymentSimulation:
    """Idempotent transitions; caller must persist atomically in a real integration."""
    # Do not process corrupted persisted amounts or an invalid simulation object.
    # Financial checks must run before idempotency checks and state transitions.
    if not isinstance(payment, PaymentSimulation):
        raise ValueError('Nieprawidłowy zapis płatności')
    from backend.payment_state_audit import audit_payment
    if not audit_payment(payment).valid:
        raise ValueError('Niespójny stan płatności')
    amounts = (payment.total_grosze, payment.products_grosze,
               payment.delivery_grosze, payment.commission_grosze,
               payment.seller_grosze, payment.refund_grosze, payment.payout_grosze)
    if any(type(value) is not int or value < 0 for value in amounts):
        raise ValueError('Nieprawidłowe kwoty płatności')
    if (payment.total_grosze != payment.products_grosze + payment.delivery_grosze
            or payment.total_grosze != payment.commission_grosze + payment.seller_grosze
            or payment.commission_grosze > payment.products_grosze
            or payment.refund_grosze > payment.total_grosze
            or payment.payout_grosze > payment.seller_grosze):
        raise ValueError('Niespójne rozliczenie płatności')
    if type(event) is not str:
        raise ValueError('Nieprawidłowe zdarzenie płatności')
    if not isinstance(event_id, str) or not event_id.strip() or len(event_id) > 128:
        raise ValueError('Nieprawidłowy identyfikator zdarzenia')
    if event_id in payment.processed_event_ids:
        return payment
    transitions = {
        ('awaiting_payment', 'payment_success_test'): ('paid_test', 0, 0),
        ('awaiting_payment', 'payment_failed_test'): ('failed_test', 0, 0),
        ('paid_test', 'delivery_failed_by_courier_test'): ('refunded_test', payment.total_grosze, 0),
        ('paid_test', 'customer_cancel_refund_test'): ('refunded_test', payment.total_grosze, 0),
        ('paid_test', 'order_completed_test'): ('completed_test', 0, 0),
        ('completed_test', 'weekly_payout_test'): ('paid_out_test', 0, payment.seller_grosze),
    }
    transition = transitions.get((payment.state, event))
    if transition is None:
        raise ValueError('Niedozwolona zmiana stanu płatności')
    state, refund, payout = transition
    return replace(payment, state=state, refund_grosze=refund, payout_grosze=payout,
                   processed_event_ids=payment.processed_event_ids | {event_id})
