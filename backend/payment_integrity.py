"""Read-only audit of offline payment simulations (not a payment processor)."""


def audit_payment_integrity(con):
    """Return private-safe issue codes; caller supplies a consistent read transaction."""
    from backend.payment_store import get_payment, validate_payment_history, validate_order_refund
    from backend.payment_state_audit import audit_payment
    issues = []
    rows = con.execute('''SELECT p.*, o.subtotal_grosze AS order_products,
        o.delivery_grosze AS order_delivery, o.total_grosze AS order_total,
        o.status AS order_status, o.fulfillment AS order_fulfillment,
        o.buyer_id AS order_buyer_id, o.farmer_id AS order_farmer_id
        FROM payment_simulations p LEFT JOIN orders o ON o.id=p.order_id''').fetchall()
    for row in rows:
        oid = row['order_id']
        def flag(code):
            issues.append({'order_id': oid, 'code': code})
        if row['order_total'] is None:
            flag('ORPHAN_PAYMENT')
            continue
        fields = ('total_grosze', 'products_grosze', 'delivery_grosze',
                  'commission_grosze', 'seller_grosze', 'refund_grosze', 'payout_grosze')
        if any(type(row[key]) is not int or row[key] < 0 for key in fields):
            flag('INVALID_AMOUNT')
            continue
        if (row['total_grosze'] != row['products_grosze'] + row['delivery_grosze']
            or row['total_grosze'] != row['commission_grosze'] + row['seller_grosze']
            or row['total_grosze'] != row['order_total']
            or row['products_grosze'] != row['order_products']
            or row['delivery_grosze'] != row['order_delivery']):
            flag('TOTAL_MISMATCH')
        if row['commission_grosze'] > row['products_grosze']:
            flag('COMMISSION_EXCEEDS_PRODUCTS')
        if row['refund_grosze'] > row['total_grosze'] or row['payout_grosze'] > row['seller_grosze']:
            flag('OVER_SETTLEMENT')
        if row['refund_grosze'] and row['payout_grosze']:
            flag('REFUND_AND_PAYOUT')
        if row['state'] == 'refunded_test':
            if row['refund_grosze'] != row['total_grosze'] or row['payout_grosze']:
                flag('INCOMPLETE_REFUND')
            if row['order_status'] not in ('nieudana_dostawa_testowo', 'anulowane_testowo'):
                flag('REFUND_ORDER_STATUS_MISMATCH')
        elif row['refund_grosze']:
            flag('UNEXPECTED_REFUND')
        if row['state'] == 'paid_out_test':
            if row['payout_grosze'] != row['seller_grosze']:
                flag('INCOMPLETE_PAYOUT')
            if row['order_status'] != 'odebrane':
                flag('PAYOUT_ORDER_STATUS_MISMATCH')
        elif row['payout_grosze']:
            flag('UNEXPECTED_PAYOUT')
        payment = get_payment(con, oid)
        if not audit_payment(payment).valid:
            flag('INVALID_PAYMENT_STATE')
        else:
            try:
                validate_payment_history(con, payment)
            except ValueError:
                flag('PAYMENT_HISTORY_MISMATCH')
            order = {'id': oid, 'status': row['order_status'],
                     'fulfillment': row['order_fulfillment'], 'buyer_id': row['order_buyer_id'],
                     'farmer_id': row['order_farmer_id']}
            try:
                validate_order_refund(con, payment, order)
            except ValueError:
                flag('REFUND_CONTEXT_MISMATCH')
    orphan_events = con.execute('''SELECT e.order_id FROM payment_simulation_events e
        LEFT JOIN payment_simulations p ON p.order_id=e.order_id
        WHERE p.order_id IS NULL''').fetchall()
    for row in orphan_events:
        issues.append({'order_id': row['order_id'], 'code': 'ORPHAN_EVENT'})
    return {'checked_payments': len(rows), 'issues': issues, 'ok': not issues}
