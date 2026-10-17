"""Read-only diagnostics must expose the same broken evidence rejected by writes."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from backend import app as api
from backend.payment_integrity import audit_payment_integrity
from scripts.run_tests_isolated import test_environment as isolated_environment
from tests.test_purchase_records import purchase
from tests.test_refund_retry_integrity import pay
from tests.test_transaction_session_boundaries import database_digest


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    target = tmp_path / 'case.sqlite'
    with closing(sqlite3.connect(target)) as dest, api.db() as source:
        source.backup(dest)
    monkeypatch.setattr(api, 'DB_PATH', str(target))


def refunded(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=True)
    for oid in ids:
        pay(client, buyer, oid)
    assert client.post(f'/shipments/{receipt["shipment_id"]}/cancel-paid-test', headers=buyer).status_code == 200
    return ids


@pytest.mark.parametrize('corruption,code', [
    (None, None), ('unknown-state', 'INVALID_PAYMENT_STATE'),
    ('missing-history', 'PAYMENT_HISTORY_MISMATCH'), ('wrong-history-state', 'PAYMENT_HISTORY_MISMATCH'),
    ('refund-reason', 'REFUND_CONTEXT_MISMATCH'), ('missing-closure', 'REFUND_CONTEXT_MISMATCH'),
    ('wrong-actor', 'REFUND_CONTEXT_MISMATCH'), ('duplicate-closure', 'REFUND_CONTEXT_MISMATCH'),
])
def test_audit_reports_history_and_closure_without_changing_data(monkeypatch, corruption, code):
    oid = refunded(monkeypatch)[-1]
    with api.db() as con:
        if corruption == 'unknown-state':
            con.execute("UPDATE payment_simulations SET state='unknown',refund_grosze=0 WHERE order_id=?", (oid,))
        elif corruption == 'missing-history':
            con.execute("DELETE FROM payment_simulation_events WHERE order_id=? AND event_type='payment_success_test'", (oid,))
        elif corruption == 'wrong-history-state':
            con.execute("UPDATE payment_simulation_events SET state_after='paid_test' WHERE order_id=? AND state_after='refunded_test'", (oid,))
        elif corruption == 'refund-reason':
            con.execute("UPDATE payment_simulation_events SET event_type='delivery_failed_by_courier_test' WHERE order_id=? AND state_after='refunded_test'", (oid,))
        elif corruption == 'missing-closure':
            con.execute("DELETE FROM order_events WHERE order_id=? AND new_status='anulowane_testowo'", (oid,))
        elif corruption == 'wrong-actor':
            con.execute("UPDATE order_events SET actor_id=NULL WHERE order_id=? AND new_status='anulowane_testowo'", (oid,))
        elif corruption == 'duplicate-closure':
            con.execute('''INSERT INTO order_events(order_id,actor_id,event_type,previous_status,new_status,created_at)
                SELECT order_id,actor_id,event_type,previous_status,new_status,created_at FROM order_events
                WHERE order_id=? AND new_status='anulowane_testowo' ''', (oid,))
    before = database_digest()
    with api.db() as con:
        con.execute('PRAGMA query_only=ON')
        con.execute('BEGIN')
        result = audit_payment_integrity(con)
        assert con.in_transaction
    if code:
        assert not result['ok'] and {'order_id': oid, 'code': code} in result['issues']
    else:
        assert result['ok'] and result['checked_payments'] == 2
    assert all(set(issue) == {'order_id', 'code'} for issue in result['issues'])
    assert database_digest() == before


def cli(path):
    return subprocess.run([sys.executable, '-m', 'scripts.audit_test_payments', '--sqlite', str(path)],
                          cwd=Path(__file__).resolve().parents[1],
                          env=isolated_environment({key: os.environ[key] for key in
                              ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP') if key in os.environ}, path),
                          capture_output=True, text=True, encoding='utf-8', timeout=20)


@pytest.mark.parametrize('name', ['audit.sqlite', 'synthetic #% audit.sqlite'])
def test_cli_uses_read_only_encoded_path(monkeypatch, tmp_path, name):
    refunded(monkeypatch)
    path = tmp_path / name
    with closing(sqlite3.connect(path)) as dest, api.db() as source:
        source.backup(dest)
    before = path.read_bytes()
    names = sorted(p.name for p in tmp_path.iterdir())
    result = cli(path)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['ok']
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == names


def test_cli_rejects_invalid_schema_without_traceback_or_path(tmp_path):
    path = tmp_path / 'private-audit.sqlite'
    with closing(sqlite3.connect(path)) as con:
        con.execute('CREATE TABLE unrelated(id INTEGER)')
    before = path.read_bytes()
    result = cli(path)
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert not report['ok'] and report['complete'] is False
    assert str(path) not in result.stdout + result.stderr
    assert 'Traceback' not in result.stdout + result.stderr
    assert path.read_bytes() == before


def test_cli_does_not_create_missing_database(tmp_path):
    path = tmp_path / 'missing.sqlite'
    result = cli(path)
    assert result.returncode == 2 and not path.exists()
