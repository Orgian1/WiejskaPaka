"""Atomic test-only reservation of a fully reconciled weekly plan; no funds move."""
from backend.payout_reconciliation import reconcile_plan

SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS payout_reservations (
 id INTEGER PRIMARY KEY,
 batch_id INTEGER NOT NULL UNIQUE REFERENCES payout_plan_batches(id),
 farmer_id INTEGER NOT NULL REFERENCES users(id),
 amount_grosze INTEGER NOT NULL CHECK(amount_grosze>0),
 status TEXT NOT NULL CHECK(status IN ('reserved_test','cancelled_test')),
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payout_reservation_items (
 order_id INTEGER PRIMARY KEY REFERENCES payment_simulations(order_id),
 reservation_id INTEGER NOT NULL REFERENCES payout_reservations(id),
 amount_grosze INTEGER NOT NULL CHECK(amount_grosze>=0)
);
'''

def reserve_plan(con, farmer_id, payout_date, now):
    """Caller MUST hold write transaction (SQLite BEGIN IMMEDIATE / PG row lock)."""
    check = reconcile_plan(con, farmer_id, payout_date)
    if check is None:
        raise ValueError('Nie znaleziono planu')
    existing = con.execute('SELECT id,amount_grosze,created_at FROM payout_reservations WHERE batch_id=? AND farmer_id=?', (check['batch_id'],farmer_id)).fetchone()
    if existing:
        status_row = con.execute('SELECT status FROM payout_reservations WHERE id=?',(existing['id'],)).fetchone()
        if status_row['status'] == 'cancelled_test':
            raise ValueError('Rezerwacja została anulowana i nie może być ponowiona')
        return {'reservation_id':existing['id'], 'amount_grosze':existing['amount_grosze'], 'created_at':existing['created_at'], 'status':'reserved_test', 'transfer_executed':False}
    if check['status'] != 'verified_test' or not check['checks'] or check['eligible_seller_grosze'] <= 0:
        raise ValueError('Plan nie przeszedł kontroli lub jest pusty')
    # Reject any already reserved order (including stale plans).
    for item in check['checks']:
        if con.execute('SELECT 1 FROM payout_reservation_items WHERE order_id=?',(item['order_id'],)).fetchone():
            raise ValueError('Zamówienie ma już rezerwację')
    insert_sql = 'INSERT INTO payout_reservations(batch_id,farmer_id,amount_grosze,status,created_at) VALUES(?,?,?,?,?)'
    cur = con.execute(insert_sql,
                      (check['batch_id'],farmer_id,check['eligible_seller_grosze'],'reserved_test',now))
    reservation_id=cur.lastrowid
    from backend.payout_batches import get_plan
    for item in get_plan(con,farmer_id,payout_date)['items']:
        con.execute('INSERT INTO payout_reservation_items(order_id,reservation_id,amount_grosze) VALUES(?,?,?)',
                    (item['order_id'],reservation_id,item['seller_grosze']))
    return {'reservation_id':reservation_id,'amount_grosze':check['eligible_seller_grosze'], 'created_at':now,'status':'reserved_test','transfer_executed':False}
