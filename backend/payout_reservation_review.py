"""Test-only revalidation and cancellation of reserved payout plans."""
from backend.payout_reconciliation import reconcile_plan


def review_reservation(con, farmer_id, payout_date):
    row = con.execute('''SELECT r.id,r.batch_id,r.amount_grosze,r.status,r.created_at
        FROM payout_reservations r JOIN payout_plan_batches b ON b.id=r.batch_id
        WHERE r.farmer_id=? AND b.payout_date=?''', (farmer_id,payout_date)).fetchone()
    if row is None:
        return None
    check = reconcile_plan(con,farmer_id,payout_date)
    reasons=[]
    if check is None or check['status'] != 'verified_test':
        reasons.append('Plan nie przechodzi ponownej kontroli')
    elif check['eligible_seller_grosze'] != row['amount_grosze']:
        reasons.append('Zmieniła się kwota należności')
    if row['status'] == 'cancelled_test':
        reasons.append('Rezerwacja została anulowana')
    return {'reservation_id':row['id'],'status':row['status'],
            'amount_grosze':row['amount_grosze'], 'valid_test':not reasons,
            'reasons':reasons, 'transfer_executed':False}


def cancel_reservation(con,farmer_id,payout_date):
    """Caller holds write transaction and (on PG) farmer row lock."""
    report=review_reservation(con,farmer_id,payout_date)
    if report is None:
        raise ValueError('Nie znaleziono rezerwacji')
    if report['status'] == 'cancelled_test':
        return report
    con.execute("UPDATE payout_reservations SET status='cancelled_test' WHERE id=? AND farmer_id=?",
                (report['reservation_id'],farmer_id))
    # Preserve historical reservation items: do not silently free orders for another plan.
    return review_reservation(con,farmer_id,payout_date)
