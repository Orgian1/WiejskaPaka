"""Regression tests for identity retrieval used by weekly payouts."""
from backend.pg_adapter import PgConnection, translate_sql


class FakeCursor:
    rowcount = 1
    def __init__(self):
        self.fetched = False
    def fetchone(self):
        self.fetched = True
        return {'id': 42}


class FakeConnection:
    def __init__(self):
        self.statements = []
        self.last_cursor = None
    def execute(self, statement, params):
        self.statements.append((statement, params))
        self.last_cursor = FakeCursor()
        return self.last_cursor


def test_payout_batch_insert_returns_identity():
    sql = translate_sql('INSERT INTO payout_plan_batches(farmer_id,payout_date,created_at) VALUES(?,?,?)')
    assert sql.endswith('RETURNING id')
    assert sql.count('%s') == 3


def test_reservation_insert_returns_identity():
    sql = translate_sql('INSERT INTO payout_reservations(batch_id,farmer_id,amount_grosze,status,created_at) VALUES(?,?,?,?,?)')
    assert sql.endswith('RETURNING id')


def test_adapter_lastrowid_is_available_to_payout_code():
    raw = FakeConnection()
    cur = PgConnection(raw).execute('INSERT INTO payout_plan_batches(farmer_id,payout_date,created_at) VALUES(?,?,?)', (7,'2026-10-19','now'))
    assert cur.lastrowid == 42
    assert raw.last_cursor.fetched


def test_adapter_does_not_consume_nonreturning_select():
    raw = FakeConnection()
    cur = PgConnection(raw).execute('SELECT id FROM payout_plan_batches WHERE id=?', (42,))
    assert cur.lastrowid is None
    assert not raw.last_cursor.fetched
