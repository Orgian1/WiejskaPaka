"""Manual weekly payout preparation. No background scheduler and no money movement."""
from datetime import date
from backend.payout_batches import create_plan
from backend.payout_auto_review import invalidate_stale_reservations

SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS payout_schedule_runs (
 payout_date TEXT PRIMARY KEY,
 created_at TEXT NOT NULL,
 farmer_count INTEGER NOT NULL CHECK(farmer_count>=0),
 plan_count INTEGER NOT NULL CHECK(plan_count>=0),
 cancelled_count INTEGER NOT NULL CHECK(cancelled_count>=0)
);
'''

def prepare_weekly_run(con, payout_date, now):
    """Call within a serialized write transaction; replay is idempotent."""
    day = date.fromisoformat(payout_date)
    if day.weekday() != 0:
        raise ValueError('Rozliczenia można przygotować wyłącznie na poniedziałek')
    previous = con.execute('SELECT * FROM payout_schedule_runs WHERE payout_date=?', (payout_date,)).fetchone()
    if previous:
        return {**dict(previous), 'already_prepared': True, 'transfer_executed': False}
    farmers = con.execute("SELECT id FROM users WHERE role='rolnik' ORDER BY id").fetchall()
    plans = cancelled = 0
    for farmer in farmers:
        farmer_id = farmer['id']
        cancelled += invalidate_stale_reservations(con, farmer_id)['cancelled_count']
        result = create_plan(con, farmer_id, payout_date, now)
        if result['status'] == 'plan_test_only':
            plans += 1
    con.execute('INSERT INTO payout_schedule_runs(payout_date,created_at,farmer_count,plan_count,cancelled_count) VALUES(?,?,?,?,?)',
                (payout_date,now,len(farmers),plans,cancelled))
    return {'payout_date':payout_date,'created_at':now,'farmer_count':len(farmers),
            'plan_count':plans,'cancelled_count':cancelled,
            'already_prepared':False,'transfer_executed':False}
