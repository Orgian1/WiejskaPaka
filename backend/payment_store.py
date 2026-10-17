"""Durable offline payment simulation; never contacts payment providers."""
from backend.payment_simulator import new_payment, apply_event, PaymentSimulation

SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS payment_simulations (
 order_id INTEGER PRIMARY KEY REFERENCES orders(id),
 total_grosze INTEGER NOT NULL CHECK(total_grosze>0),
 products_grosze INTEGER NOT NULL CHECK(products_grosze>=0),
 delivery_grosze INTEGER NOT NULL CHECK(delivery_grosze>=0),
 commission_grosze INTEGER NOT NULL CHECK(commission_grosze>=0),
 seller_grosze INTEGER NOT NULL CHECK(seller_grosze>=0),
 state TEXT NOT NULL,
 refund_grosze INTEGER NOT NULL DEFAULT 0 CHECK(refund_grosze>=0),
 payout_grosze INTEGER NOT NULL DEFAULT 0 CHECK(payout_grosze>=0),
 CHECK(total_grosze=products_grosze+delivery_grosze),
 CHECK(total_grosze=commission_grosze+seller_grosze)
);
CREATE TABLE IF NOT EXISTS payment_simulation_events (
 event_id TEXT PRIMARY KEY,
 order_id INTEGER NOT NULL REFERENCES payment_simulations(order_id),
 event_type TEXT NOT NULL,
 state_after TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS payment_events_order_idx ON payment_simulation_events(order_id,created_at);
'''


def get_payment(con, order_id):
    row = con.execute('SELECT * FROM payment_simulations WHERE order_id=?', (order_id,)).fetchone()
    if row is None:
        return None
    events = con.execute('SELECT event_id FROM payment_simulation_events WHERE order_id=?', (order_id,)).fetchall()
    return PaymentSimulation(row['order_id'], row['total_grosze'], row['products_grosze'],
        row['delivery_grosze'], row['commission_grosze'], row['seller_grosze'], row['state'],
        row['refund_grosze'], row['payout_grosze'], frozenset(e['event_id'] for e in events))


def validate_order_payment(payment, order):
    """Validate persisted money against its order, including idempotent retries."""
    from backend.payment_state_audit import audit_payment
    if not audit_payment(payment).valid:
        raise ValueError('Niespójny stan płatności')
    fields = ('subtotal_grosze', 'delivery_grosze', 'total_grosze')
    if (any(type(order[key]) is not int or order[key] < 0 for key in fields)
            or order['total_grosze'] <= 0
            or order['subtotal_grosze'] + order['delivery_grosze'] != order['total_grosze']
            or (payment.order_id, payment.products_grosze, payment.delivery_grosze, payment.total_grosze)
            != (order['id'], order['subtotal_grosze'], order['delivery_grosze'], order['total_grosze'])):
        raise ValueError('Niespójna kwota zamówienia i płatności')


def create_payment(con, order):
    existing = get_payment(con, order['id'])
    if existing is not None:
        validate_order_payment(existing, order)
        return existing
    payment = new_payment(order['id'], order['subtotal_grosze'], order['delivery_grosze'])
    if payment.total_grosze != order['total_grosze']:
        raise ValueError('Niespójna kwota zamówienia')
    con.execute('''INSERT INTO payment_simulations(order_id,total_grosze,products_grosze,delivery_grosze,
        commission_grosze,seller_grosze,state,refund_grosze,payout_grosze)
        VALUES(?,?,?,?,?,?,?,?,?)''', (payment.order_id,payment.total_grosze,payment.products_grosze,
        payment.delivery_grosze,payment.commission_grosze,payment.seller_grosze,payment.state,0,0))
    return payment


def persist_event(con, payment, event_id, event_type, timestamp):
    from backend.payment_state_audit import audit_payment
    if not audit_payment(payment).valid:
        raise ValueError('Niespójny stan płatności')
    previous = con.execute('SELECT order_id,event_type FROM payment_simulation_events WHERE event_id=?', (event_id,)).fetchone()
    if previous:
        if previous['order_id'] != payment.order_id or previous['event_type'] != event_type:
            raise ValueError('Identyfikator zdarzenia został użyty do innej operacji')
        return payment
    updated = apply_event(payment, event_id, event_type)
    # Compare-and-swap: nie nadpisuj stanu zmienionego przez równoległą transakcję.
    changed = con.execute('''UPDATE payment_simulations SET state=?,refund_grosze=?,payout_grosze=?
                             WHERE order_id=? AND state=? AND refund_grosze=? AND payout_grosze=?''',
                (updated.state, updated.refund_grosze, updated.payout_grosze, payment.order_id,
                 payment.state, payment.refund_grosze, payment.payout_grosze))
    if changed.rowcount != 1:
        raise ValueError('Stan płatności zmienił się równolegle; ponów operację')
    con.execute('''INSERT INTO payment_simulation_events(event_id,order_id,event_type,state_after,created_at)
                   VALUES(?,?,?,?,?)''', (event_id,payment.order_id,event_type,updated.state,timestamp))
    return updated


def public_payment(payment):
    return {k: getattr(payment, k) for k in ('order_id','total_grosze','products_grosze','delivery_grosze',
            'commission_grosze','seller_grosze','state','refund_grosze','payout_grosze')}
