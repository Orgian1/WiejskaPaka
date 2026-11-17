"""Pure payment-state transition guard, independent of PayU network access.

A webhook's authenticity must be verified *before* calling this guard.
State transitions alone never credit a wallet.
"""
from backend.payu_preparation import PaymentStatus


_ALLOWED = {
    PaymentStatus.CREATED: {PaymentStatus.PENDING, PaymentStatus.CONFIRMED,
                            PaymentStatus.FAILED, PaymentStatus.CANCELLED},
    PaymentStatus.PENDING: {PaymentStatus.CONFIRMED, PaymentStatus.FAILED,
                            PaymentStatus.CANCELLED},
    PaymentStatus.CONFIRMED: {PaymentStatus.REFUNDED},
    PaymentStatus.FAILED: set(),
    PaymentStatus.CANCELLED: set(),
    PaymentStatus.REFUNDED: set(),
}


def payment_transition(current: PaymentStatus, incoming: PaymentStatus) -> bool:
    """Return True only for a new permitted transition, False for duplicate.

    Raises ValueError for invalid transitions or non-enum values. Out-of-order
    failure callbacks must not undo a confirmed transaction.
    """
    if type(current) is not PaymentStatus or type(incoming) is not PaymentStatus:
        raise ValueError("Payment statuses must be typed enums")
    if current == incoming:
        return False
    if incoming not in _ALLOWED[current]:
        raise ValueError(f"Disallowed payment transition: {current} -> {incoming}")
    return True
