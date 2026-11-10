"""Internal, read-only monthly operational report for TEST payments.

Not a VAT ledger, invoice register, bank statement or revenue recognition engine.
"""
import re

_MONTH = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')
_ELIGIBLE = frozenset({'completed_test', 'paid_out_test'})


def validate_month(month: str) -> str:
    if not isinstance(month, str) or not _MONTH.fullmatch(month):
        raise ValueError('Miesiąc musi mieć format RRRR-MM')
    return month


def monthly_platform_report(con, month: str):
    """Snapshot by first qualifying TEST event month; only currently eligible payments.

    Refunds or changed states remove an order from eligible commission totals.
    Historical gross and refund volumes are separately reported by event timestamp.
    """
    validate_month(month)
    events = con.execute('''SELECT e.order_id, e.event_id, e.event_type, e.state_after,
                                  e.created_at, p.state AS current_state,
                                  p.total_grosze, p.products_grosze, p.delivery_grosze,
                                  p.commission_grosze, p.seller_grosze, p.refund_grosze
                           FROM payment_simulation_events e
                           JOIN payment_simulations p ON p.order_id=e.order_id
                           ORDER BY e.created_at, e.event_id''').fetchall()
    first_completed = {}
    paid_events = set()
    refund_events = set()
    for row in events:
        r = dict(row)
        if r['state_after'] in _ELIGIBLE and r['order_id'] not in first_completed:
            first_completed[r['order_id']] = r
        if str(r['created_at']).startswith(month):
            if r['event_type'] == 'payment_success_test':
                paid_events.add(r['order_id'])
            if r['event_type'] in ('delivery_failed_by_courier_test', 'customer_cancel_refund_test'):
                refund_events.add(r['order_id'])
    eligible = [r for r in first_completed.values()
                if str(r['created_at']).startswith(month) and r['current_state'] in _ELIGIBLE]
    return {
        'month': month,
        'report_type': 'test_operational_snapshot_not_accounting',
        'eligible_order_count': len(eligible),
        'products_grosze': sum(r['products_grosze'] for r in eligible),
        'delivery_grosze': sum(r['delivery_grosze'] for r in eligible),
        'gross_order_grosze': sum(r['total_grosze'] for r in eligible),
        'platform_commission_grosze': sum(r['commission_grosze'] for r in eligible),
        'seller_due_grosze': sum(r['seller_grosze'] for r in eligible),
        'payment_success_event_order_count': len(paid_events),
        'refund_event_order_count': len(refund_events),
        'limitations': 'Symulacja: bez opłat PSP, VAT, KSeF, rzeczywistych wpłat i korekt księgowych.'
    }
