"""Read-only seller payout and platform commission reports (test payments only)."""
from datetime import date, timedelta

ELIGIBLE = 'completed_test'
PAID = 'paid_out_test'

def next_weekly_date(today: date, weekday: int = 0) -> date:
    if not isinstance(today, date) or not 0 <= weekday <= 6:
        raise ValueError('Nieprawidłowa data lub dzień tygodnia')
    return today + timedelta(days=(weekday - today.weekday()) % 7)

def summarize(rows):
    """Only completed orders become payable; refunded/failed/paid are excluded."""
    result = {'eligible_grosze': 0, 'paid_out_grosze': 0, 'pending_grosze': 0,
              'platform_commission_earned_grosze': 0, 'platform_commission_paid_out_grosze': 0,
              'eligible_orders': 0, 'paid_orders': 0}
    for row in rows:
        state = row['state']
        seller = row['seller_grosze']
        commission = row['commission_grosze']
        if state == ELIGIBLE:
            result['eligible_grosze'] += seller
            result['pending_grosze'] += seller
            result['platform_commission_earned_grosze'] += commission
            result['eligible_orders'] += 1
        elif state == PAID:
            result['paid_out_grosze'] += row['payout_grosze']
            result['platform_commission_earned_grosze'] += commission
            result['platform_commission_paid_out_grosze'] += commission
            result['paid_orders'] += 1
    return result


def seller_report(con, farmer_id: int):
    rows = con.execute('''SELECT p.order_id,p.state,p.total_grosze,p.commission_grosze,
        p.seller_grosze,p.payout_grosze,p.refund_grosze
        FROM payment_simulations p JOIN orders o ON o.id=p.order_id
        WHERE o.farmer_id=? ORDER BY p.order_id''', (farmer_id,)).fetchall()
    return {'farmer_id': farmer_id, **summarize(rows),
            'orders': [dict(r) for r in rows]}
