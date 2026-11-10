"""SQLite integration: atomicity, idempotency, stale writes, and serialized writers."""
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.payment_store import SCHEMA_SQLITE, create_payment, get_payment, persist_event


def setup(path):
    con = sqlite3.connect(path)
    con.execute('PRAGMA foreign_keys=ON')
    con.executescript('CREATE TABLE orders(id INTEGER PRIMARY KEY);' + SCHEMA_SQLITE)
    con.execute('INSERT INTO orders(id) VALUES(1)')
    con.execute('INSERT INTO orders(id) VALUES(2)')
    con.row_factory = sqlite3.Row
    create_payment(con, dict(id=1, subtotal_grosze=1001, delivery_grosze=100, total_grosze=1101))
    create_payment(con, dict(id=2, subtotal_grosze=1001, delivery_grosze=100, total_grosze=1101))
    con.commit()
    con.close()


def connect(path):
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con


def test_replay_and_cross_order_event_collision(tmp_path):
    path = tmp_path / 'payments.db'
    setup(path)
    with connect(path) as con:
        con.execute('BEGIN IMMEDIATE')
        payment = get_payment(con, 1)
        first = persist_event(con, payment, 'evt1', 'payment_success_test', 'now')
        assert first.state == 'paid_test'
        assert persist_event(con, get_payment(con, 1), 'evt1', 'payment_success_test', 'now').state == 'paid_test'
        with pytest.raises(ValueError, match='innej operacji'):
            persist_event(con, get_payment(con, 2), 'evt1', 'payment_success_test', 'now')
    with connect(path) as con:
        assert con.execute('SELECT count(*) FROM payment_simulation_events').fetchone()[0] == 1


def test_stale_snapshot_cannot_overwrite_state(tmp_path):
    path = tmp_path / 'payments.db'
    setup(path)
    with connect(path) as con:
        stale = get_payment(con, 1)
        persist_event(con, stale, 'first', 'payment_success_test', 'now')
        with pytest.raises(ValueError, match='równolegle'):
            persist_event(con, stale, 'second', 'payment_failed_test', 'now')
        assert get_payment(con, 1).state == 'paid_test'
        assert con.execute('SELECT count(*) FROM payment_simulation_events').fetchone()[0] == 1


def test_two_writers_only_one_transition(tmp_path):
    path = tmp_path / 'payments.db'
    setup(path)
    start = threading.Barrier(2)

    def worker(event_id, event_type):
        start.wait(timeout=10)
        con = connect(path)
        try:
            con.execute('BEGIN IMMEDIATE')
            try:
                payment = get_payment(con, 1)
                persist_event(con, payment, event_id, event_type, 'now')
                con.commit()
                return 'ok'
            except ValueError:
                con.rollback()
                return 'rejected'
        finally:
            con.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, 'success', 'payment_success_test'),
                   pool.submit(worker, 'failed', 'payment_failed_test')]
        assert sorted(f.result() for f in futures) == ['ok', 'rejected']
    with connect(path) as con:
        assert con.execute('SELECT count(*) FROM payment_simulation_events').fetchone()[0] == 1
        assert get_payment(con, 1).state in ('paid_test', 'failed_test')
