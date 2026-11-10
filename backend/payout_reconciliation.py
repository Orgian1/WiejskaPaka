"""Read-only reconciliation of test payout plan snapshots against current payment/order state."""

def reconcile_plan(con, farmer_id, payout_date):
    from backend.payout_batches import get_plan
    plan = get_plan(con, farmer_id, payout_date)
    if plan is None:
        return None
    checks = []
    for item in plan['items']:
        row = con.execute('''SELECT o.farmer_id,o.status,p.state,p.refund_grosze,p.payout_grosze,
                     p.seller_grosze,p.commission_grosze
                     FROM orders o LEFT JOIN payment_simulations p ON p.order_id=o.id
                     WHERE o.id=?''', (item['order_id'],)).fetchone()
        problems = []
        if row is None or row['farmer_id'] != farmer_id:
            problems.append('order_missing_or_owner_changed')
        else:
            if row['status'] != 'odebrane':
                problems.append('order_not_collected')
            if row['state'] != 'completed_test':
                problems.append('payment_not_completed')
            if row['refund_grosze']:
                problems.append('refund_recorded')
            if row['payout_grosze']:
                problems.append('already_paid_test')
            if (row['seller_grosze'] != item['seller_grosze'] or
                    row['commission_grosze'] != item['commission_grosze']):
                problems.append('amount_changed')
        checks.append({'order_id': item['order_id'], 'eligible': not problems, 'problems': problems})
    blocked = any(not x['eligible'] for x in checks)
    return {'batch_id': plan['id'], 'payout_date': payout_date,
            'status': 'blocked_test' if blocked else 'verified_test',
            'checks': checks, 'eligible_seller_grosze': sum(
                item['seller_grosze'] for item, check in zip(plan['items'], checks) if check['eligible']),
            'planned_seller_grosze': plan['seller_total_grosze'],
            'transfer_executed': False,
            'notice': 'Kontrola informacyjna. Nie zatwierdza ani nie wykonuje wypłat.'}
