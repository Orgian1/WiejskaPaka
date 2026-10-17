"""Test-market inventory holds. No payment, deduction or customer refund is made."""
from datetime import datetime, timedelta, timezone
from backend.time_safety import utc_datetime

HOLD_MINUTES = 30
PENDING = 'oczekuje_na_platnosc_testowa'
CANCELLED = 'anulowane_testowo'
UNPAID = frozenset({'awaiting_payment', 'failed_test'})
SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS inventory_reservations (
    order_id INTEGER PRIMARY KEY REFERENCES orders(id),
    expires_at TEXT NOT NULL,
    released_at TEXT
);
CREATE INDEX IF NOT EXISTS inventory_reservations_expiry
    ON inventory_reservations(expires_at) WHERE released_at IS NULL;
'''


def add_hold(con, order_id, *, now):
    deadline = utc_datetime(now) + timedelta(minutes=HOLD_MINUTES)
    con.execute('INSERT INTO inventory_reservations(order_id,expires_at) VALUES(?,?)',
                (order_id, deadline.isoformat()))
    return deadline.isoformat()


def payment_deadline_passed(con, order_id, *, now):
    row = con.execute('SELECT expires_at,released_at FROM inventory_reservations WHERE order_id=?',
                      (order_id,)).fetchone()
    # Legacy orders deliberately have no inferred deadline.
    return row is not None and (row['released_at'] is not None or
                                utc_datetime(row['expires_at']) <= utc_datetime(now))


def expire_due(con, *, now, postgres=False, record_event, limit=100):
    """Caller owns the transaction; lock whole shipments before releasing stock.

    Paid, partially paid, fulfilled and legacy shipments are left untouched.
    PostgreSQL order locks serialize this job against the payment writer. SQLite
    callers must start BEGIN IMMEDIATE before calling. All changes roll back
    together on failure, including notifications and inventory restoration.
    """
    instant = utc_datetime(now)
    stamp = instant.isoformat()
    candidates = con.execute('''SELECT r.order_id FROM inventory_reservations r
        JOIN orders o ON o.id=r.order_id
        WHERE r.released_at IS NULL AND r.expires_at<=? AND o.status=?
        AND o.pin_used=0 AND o.confirmed_at IS NULL
        AND NOT EXISTS (SELECT 1 FROM payment_simulations p WHERE p.order_id=o.id
            AND (p.state NOT IN ('awaiting_payment','failed_test') OR p.refund_grosze<>0 OR p.payout_grosze<>0))
        AND NOT EXISTS (
            SELECT 1 FROM shipment_order_links own
            JOIN shipment_order_links other ON other.shipment_id=own.shipment_id
            JOIN orders sibling ON sibling.id=other.order_id
            LEFT JOIN inventory_reservations h ON h.order_id=sibling.id
            LEFT JOIN payment_simulations p ON p.order_id=sibling.id
            WHERE own.order_id=o.id AND (sibling.status<>? OR sibling.pin_used<>0
                OR sibling.confirmed_at IS NOT NULL OR h.order_id IS NULL
                OR h.released_at IS NOT NULL OR h.expires_at>?
                OR (p.order_id IS NOT NULL AND (p.state NOT IN ('awaiting_payment','failed_test')
                    OR p.refund_grosze<>0 OR p.payout_grosze<>0))))
        ORDER BY r.expires_at,r.order_id LIMIT ?''', (stamp, PENDING, PENDING, stamp, limit)).fetchall()
    seen = set()
    expired = 0
    for candidate in candidates:
        oid = candidate['order_id']
        if oid in seen:
            continue
        link = con.execute('SELECT shipment_id FROM shipment_order_links WHERE order_id=?', (oid,)).fetchone()
        suffix = ' FOR UPDATE OF o' if postgres else ''
        if link:
            # Match the lock order of shipment cancellation/confirmation.
            con.execute('SELECT id FROM shipment_groups WHERE id=?' + (' FOR UPDATE' if postgres else ''),
                        (link['shipment_id'],)).fetchone()
            orders = con.execute('''SELECT o.* FROM orders o JOIN shipment_order_links l ON l.order_id=o.id
                WHERE l.shipment_id=? ORDER BY o.id''' + suffix, (link['shipment_id'],)).fetchall()
        else:
            orders = con.execute('SELECT o.* FROM orders o WHERE o.id=?' + suffix, (oid,)).fetchall()
        seen.update(o['id'] for o in orders)
        safe = bool(orders)
        for order in orders:
            hold = con.execute('SELECT expires_at,released_at FROM inventory_reservations WHERE order_id=?',
                               (order['id'],)).fetchone()
            payment = con.execute('SELECT state,refund_grosze,payout_grosze FROM payment_simulations WHERE order_id=?',
                                  (order['id'],)).fetchone()
            if (order['status'] != PENDING or order['pin_used'] or order['confirmed_at'] is not None
                or hold is None or hold['released_at'] is not None
                or utc_datetime(hold['expires_at']) > instant
                or (payment is not None and (payment['state'] not in UNPAID
                    or payment['refund_grosze'] != 0 or payment['payout_grosze'] != 0))):
                safe = False
                break
        if not safe:
            continue
        for order in orders:
            changed = con.execute('UPDATE orders SET status=? WHERE id=? AND status=?',
                                  (CANCELLED, order['id'], PENDING))
            if changed.rowcount != 1:
                raise RuntimeError('Reservation status changed during expiration')
            con.execute('UPDATE products SET stock=stock+? WHERE id=?', (order['quantity'], order['product_id']))
            con.execute('UPDATE inventory_reservations SET released_at=? WHERE order_id=?', (stamp, order['id']))
            # Existing actor FK uses the buyer; event type explicitly identifies the automatic job.
            record_event(con, order['id'], order['buyer_id'], 'reservation_expired_test', PENDING, CANCELLED)
            expired += 1
    return {'expired_orders': expired, 'checked_candidates': len(candidates)}


MAX_UNPAID_PURCHASES = 10


def has_hold_capacity(con, buyer_id):
    # A 50-line shipment counts once. The caller holds the buyer write lock.
    row = con.execute('''SELECT COUNT(DISTINCT CASE WHEN l.shipment_id IS NULL
            THEN 'order:' || CAST(o.id AS TEXT) ELSE 'shipment:' || l.shipment_id END) AS n
        FROM orders o JOIN inventory_reservations h ON h.order_id=o.id
        LEFT JOIN shipment_order_links l ON l.order_id=o.id
        WHERE o.buyer_id=? AND o.status=? AND h.released_at IS NULL
        AND NOT EXISTS (SELECT 1 FROM payment_simulations p WHERE p.order_id=o.id
            AND p.state NOT IN ('awaiting_payment','failed_test'))''', (buyer_id, PENDING)).fetchone()
    return row['n'] < MAX_UNPAID_PURCHASES
