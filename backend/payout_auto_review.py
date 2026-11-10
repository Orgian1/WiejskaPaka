"""Atomowa kontrola i anulowanie nieaktualnych rezerwacji TESTOWYCH."""
from backend.payout_reservation_review import review_reservation, cancel_reservation


def invalidate_stale_reservations(con, farmer_id):
    """Wywoływać w transakcji zapisu; na PostgreSQL po zablokowaniu wiersza rolnika.

    Nie dotyka rzeczywistych pieniędzy ani dyspozycji operatora.
    """
    rows = con.execute('''SELECT b.payout_date FROM payout_reservations r
        JOIN payout_plan_batches b ON b.id=r.batch_id
        WHERE r.farmer_id=? AND r.status='reserved_test'
        ORDER BY b.payout_date''', (farmer_id,)).fetchall()
    checked = 0
    cancelled = []
    for row in rows:
        date = row['payout_date']
        report = review_reservation(con, farmer_id, date)
        checked += 1
        if not report['valid_test']:
            cancel_reservation(con, farmer_id, date)
            cancelled.append({'payout_date': date, 'reservation_id': report['reservation_id'],
                              'reasons': report['reasons']})
    return {'checked': checked, 'cancelled_count': len(cancelled),
            'cancelled': cancelled, 'transfer_executed': False}
