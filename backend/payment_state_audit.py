"""Pure, offline consistency checks for test-only payment snapshots.

Never triggers transfers or changes persisted data.
"""
from dataclasses import dataclass
from backend.payment_simulator import PaymentSimulation


@dataclass(frozen=True)
class AuditResult:
    valid: bool
    issues: tuple[str, ...]


def audit_payment(p: PaymentSimulation) -> AuditResult:
    issues = []
    if not isinstance(p, PaymentSimulation):
        return AuditResult(False, ('invalid_payment_object',))
    fields = ('order_id', 'total_grosze', 'products_grosze', 'delivery_grosze',
              'commission_grosze', 'seller_grosze', 'refund_grosze', 'payout_grosze')
    if any(type(getattr(p, f)) is not int for f in fields):
        return AuditResult(False, ('non_integer_amount_or_id',))
    if p.order_id <= 0 or any(getattr(p, f) < 0 for f in fields[1:]):
        issues.append('negative_amount_or_invalid_id')
    if p.total_grosze != p.products_grosze + p.delivery_grosze:
        issues.append('total_mismatch')
    if p.total_grosze != p.commission_grosze + p.seller_grosze:
        issues.append('allocation_mismatch')
    if p.commission_grosze > p.products_grosze:
        issues.append('commission_exceeds_products')
    if not isinstance(p.processed_event_ids, frozenset) or any(
        not isinstance(x, str) or not x.strip() or len(x) > 128 for x in p.processed_event_ids
    ):
        issues.append('invalid_event_ids')
    allowed = {
        'awaiting_payment': (0, 0),
        'failed_test': (0, 0),
        'paid_test': (0, 0),
        'completed_test': (0, 0),
        'refunded_test': (p.total_grosze, 0),
        'paid_out_test': (0, p.seller_grosze),
    }
    if p.state not in allowed:
        issues.append('unknown_state')
    elif (p.refund_grosze, p.payout_grosze) != allowed[p.state]:
        issues.append('state_amount_mismatch')
    return AuditResult(not issues, tuple(issues))
