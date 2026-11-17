import sqlite3
import pytest
from backend.payu_journal_schema import initialize_test_journal
from backend.payu_journal_events import record_verified_payment_event as record
from backend.payu_preparation import PaymentStatus as S


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    initialize_test_journal(connection)
    connection.execute("INSERT INTO provider_payment_operations(operation_id,user_id,provider,amount_grosze,status) VALUES ('op-1',1,'simulated',100,'CREATED')")
    yield connection
    connection.close()


def test_verified_state_is_recorded_once_without_wallet_credit(conn):
    assert record(conn,event_id="evt-1",operation_id="op-1",incoming_status=S.CONFIRMED)
    assert not record(conn,event_id="evt-1",operation_id="op-1",incoming_status=S.CONFIRMED)
    assert conn.execute("SELECT status,credited_at FROM provider_payment_operations").fetchone() == ("CONFIRMED",None)
    assert conn.execute("SELECT COUNT(*) FROM provider_payment_events").fetchone()[0] == 1


def test_invalid_out_of_order_event_is_atomic(conn):
    record(conn,event_id="evt-1",operation_id="op-1",incoming_status=S.CONFIRMED)
    with pytest.raises(ValueError):
        record(conn,event_id="evt-2",operation_id="op-1",incoming_status=S.FAILED)
    assert conn.execute("SELECT COUNT(*) FROM provider_payment_events").fetchone()[0] == 1


def test_event_id_cannot_be_reused_for_different_state(conn):
    record(conn,event_id="evt-1",operation_id="op-1",incoming_status=S.PENDING)
    with pytest.raises(ValueError):
        record(conn,event_id="evt-1",operation_id="op-1",incoming_status=S.CONFIRMED)
    assert conn.execute("SELECT status FROM provider_payment_operations").fetchone()[0] == "PENDING"


def test_unknown_operation_never_creates_event(conn):
    with pytest.raises(ValueError):
        record(conn,event_id="evt-1",operation_id="missing",incoming_status=S.CONFIRMED)
    assert conn.execute("SELECT COUNT(*) FROM provider_payment_events").fetchone()[0] == 0
