"""Isolated SQLite journal for verified test events, never a wallet credit.

The caller must independently verify provider authenticity and order identity.
This module intentionally has no production database or wallet dependency.
"""
from backend.payu_preparation import PaymentStatus
from backend.payu_state import payment_transition


def record_verified_payment_event(conn, *, event_id: str, operation_id: str,
                                  incoming_status: PaymentStatus) -> bool:
    if not isinstance(event_id, str) or not 1 <= len(event_id) <= 120:
        raise ValueError("Invalid event ID")
    if not isinstance(operation_id, str) or not operation_id:
        raise ValueError("Invalid operation ID")
    if type(incoming_status) is not PaymentStatus:
        raise ValueError("Invalid status")
    # Transaction ownership is the responsibility of the caller. The savepoint
    # guarantees atomic rollback without committing unrelated caller changes.
    conn.execute("SAVEPOINT verified_payment_event")
    try:
        row = conn.execute("SELECT status FROM provider_payment_operations WHERE operation_id=?",
                           (operation_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown payment operation")
        duplicate = conn.execute("SELECT operation_id,event_type FROM provider_payment_events WHERE event_id=?",
                                 (event_id,)).fetchone()
        if duplicate:
            if duplicate != (operation_id, incoming_status.value):
                raise ValueError("Event ID reused for different payment details")
            conn.execute("RELEASE SAVEPOINT verified_payment_event")
            return False
        changed = payment_transition(PaymentStatus(row[0]), incoming_status)
        conn.execute("INSERT INTO provider_payment_events(event_id,operation_id,event_type,verified) VALUES (?,?,?,1)",
                     (event_id, operation_id, incoming_status.value))
        if changed:
            conn.execute("UPDATE provider_payment_operations SET status=?,updated_at=CAST(strftime('%s','now') AS INTEGER) WHERE operation_id=?",
                         (incoming_status.value, operation_id))
        conn.execute("RELEASE SAVEPOINT verified_payment_event")
        return changed
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT verified_payment_event")
        conn.execute("RELEASE SAVEPOINT verified_payment_event")
        raise
