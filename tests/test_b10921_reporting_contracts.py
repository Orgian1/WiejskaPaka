"""Real SQL result projections and persisted financial report boundaries."""
import sqlite3

import pytest

from backend.neon_order_access import buyer_orders, farmer_orders
from backend.payment_store import SCHEMA_SQLITE, create_payment, persist_event
from backend.platform_reports import monthly_platform_report
from backend.psp_reconciliation import reconcile_test_payments


@pytest.mark.parametrize('read', [buyer_orders, farmer_orders])
def test_order_projection_contains_parcel_code_required_by_frontend(read):
    with sqlite3.connect(':memory:') as con:
        con.row_factory = sqlite3.Row
        con.execute('CREATE TABLE orders(id integer,pickup_code text,product_id integer,quantity integer,total_grosze integer,fulfillment text,status text,created_at text,buyer_id integer,farmer_id integer)')
        from backend.inventory_reservations import SCHEMA_SQLITE as HOLD_SCHEMA
        con.executescript(HOLD_SCHEMA)
        con.execute("INSERT INTO orders VALUES(1,'WP-TEST',2,3,999,'odbior','odebrane','2026-10-15',42,42)")

        class BoundSQL:
            def execute(self, sql, params):
                # The SELECT is portable SQL; PostgreSQL driver binding is tested
                # separately by the opt-in native integration gate.
                return con.execute(sql.replace('%s', '?'), params)

        rows = read(BoundSQL(), 42)
        assert dict(rows[0])['pickup_code'] == 'WP-TEST'
        assert dict(rows[0])['reservation_expires_at'] is None
        con.execute("INSERT INTO inventory_reservations(order_id,expires_at) VALUES(1,'2026-10-16T12:30:00+00:00')")
        assert read(BoundSQL(), 42)[0]['reservation_expires_at'] == '2026-10-16T12:30:00+00:00'
        assert read(BoundSQL(), 43) == []


def payments():
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript('CREATE TABLE orders(id integer primary key);' + SCHEMA_SQLITE)
    con.execute('INSERT INTO orders VALUES(1)')
    payment = create_payment(con, {'id': 1, 'subtotal_grosze': 1000, 'delivery_grosze': 501, 'total_grosze': 1501})
    return con, payment


def test_awaiting_payment_cannot_reconcile_as_paid():
    con, _ = payments()
    try:
        assert reconcile_test_payments(con, [{'order_id': 1, 'amount_grosze': 1501, 'status': 'pending'}])['matched'] == 1
        assert reconcile_test_payments(con, [{'order_id': 1, 'amount_grosze': 1501, 'status': 'paid'}])['mismatched'] == 1
        con.execute("UPDATE payment_simulations SET state='unknown' WHERE order_id=1")
        assert reconcile_test_payments(con, [{'order_id': 1, 'amount_grosze': 1501, 'status': 'paid'}])['mismatched'] == 1
    finally:
        con.close()


def test_monthly_report_counts_customer_refund_as_well_as_courier_refund():
    con, payment = payments()
    try:
        paid = persist_event(con, payment, 'paid', 'payment_success_test', '2026-10-15T10:00:00Z')
        persist_event(con, paid, 'cancel', 'customer_cancel_refund_test', '2026-10-15T10:01:00Z')
        report = monthly_platform_report(con, '2026-10')
        assert report['refund_event_order_count'] == 1
        assert report['platform_commission_grosze'] == 0
        assert report['seller_due_grosze'] == 0
    finally:
        con.close()


def test_replaying_persisted_event_rejects_corrupt_snapshot():
    from dataclasses import replace
    con, payment = payments()
    try:
        paid = persist_event(con, payment, 'paid', 'payment_success_test', '2026-10-15T10:00:00Z')
        with pytest.raises(ValueError):
            persist_event(con, replace(paid, refund_grosze=1), 'paid', 'payment_success_test', 'later')
    finally:
        con.close()
