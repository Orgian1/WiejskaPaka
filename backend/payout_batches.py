"""Immutable weekly payout *plans*; no transfers or payment state changes."""
from datetime import date
from backend.payout_reports import next_weekly_date

SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS payout_plan_batches (
 id INTEGER PRIMARY KEY, farmer_id INTEGER NOT NULL REFERENCES users(id),
 payout_date TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(farmer_id,payout_date)
);
CREATE TABLE IF NOT EXISTS payout_plan_items (
 order_id INTEGER PRIMARY KEY REFERENCES payment_simulations(order_id),
 batch_id INTEGER NOT NULL REFERENCES payout_plan_batches(id),
 seller_grosze INTEGER NOT NULL CHECK(seller_grosze>=0),
 commission_grosze INTEGER NOT NULL CHECK(commission_grosze>=0)
);
CREATE INDEX IF NOT EXISTS payout_plan_items_batch_idx ON payout_plan_items(batch_id);
'''

def get_plan(con, farmer_id, payout_date):
    batch = con.execute('SELECT id,farmer_id,payout_date,created_at FROM payout_plan_batches WHERE farmer_id=? AND payout_date=?', (farmer_id,payout_date)).fetchone()
    if not batch:
        return None
    items = con.execute('''SELECT i.order_id,i.seller_grosze,i.commission_grosze
        FROM payout_plan_items i WHERE i.batch_id=? ORDER BY i.order_id''',(batch['id'],)).fetchall()
    return {'id':batch['id'],'farmer_id':batch['farmer_id'],'payout_date':batch['payout_date'],
            'created_at':batch['created_at'], 'items':[dict(x) for x in items],
            'seller_total_grosze':sum(x['seller_grosze'] for x in items),
            'commission_total_grosze':sum(x['commission_grosze'] for x in items),
            'status':'plan_test_only','transfer_executed':False}

def create_plan(con, farmer_id, payout_date, now):
    """Call inside a transaction; caller must serialize farmer plan creation."""
    if date.fromisoformat(payout_date).weekday() != 0:
        raise ValueError('Dzień rozliczenia musi przypadać w poniedziałek')
    existing = get_plan(con,farmer_id,payout_date)
    if existing:
        return existing
    # Only orders currently eligible and not assigned to any other plan.
    rows = con.execute('''SELECT p.order_id,p.seller_grosze,p.commission_grosze
      FROM payment_simulations p JOIN orders o ON o.id=p.order_id
      LEFT JOIN payout_plan_items i ON i.order_id=p.order_id
      WHERE o.farmer_id=? AND p.state='completed_test' AND i.order_id IS NULL
      ORDER BY p.order_id''',(farmer_id,)).fetchall()
    if not rows:
        return {'farmer_id':farmer_id,'payout_date':payout_date,'items':[],
                'seller_total_grosze':0,'commission_total_grosze':0,
                'status':'nothing_to_plan_test','transfer_executed':False}
    cur=con.execute('INSERT INTO payout_plan_batches(farmer_id,payout_date,created_at) VALUES(?,?,?)',
                    (farmer_id,payout_date,now))
    batch_id=cur.lastrowid
    for row in rows:
        con.execute('''INSERT INTO payout_plan_items(order_id,batch_id,seller_grosze,commission_grosze)
          VALUES(?,?,?,?)''',(row['order_id'],batch_id,row['seller_grosze'],row['commission_grosze']))
    return get_plan(con,farmer_id,payout_date)
