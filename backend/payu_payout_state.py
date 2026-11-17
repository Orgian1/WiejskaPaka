"""Payout state machine for a future approved operator contract.

Transitions are local validation only; no real transfer occurs here.
"""
from backend.payu_preparation import PayoutStatus


_ALLOWED = {
    PayoutStatus.REQUESTED: {PayoutStatus.APPROVED, PayoutStatus.REJECTED},
    PayoutStatus.APPROVED: {PayoutStatus.SENT, PayoutStatus.REJECTED, PayoutStatus.FAILED},
    PayoutStatus.SENT: {PayoutStatus.SETTLED, PayoutStatus.FAILED},
    PayoutStatus.SETTLED: set(),
    PayoutStatus.REJECTED: set(),
    PayoutStatus.FAILED: set(),
}


def payout_transition(current: PayoutStatus, incoming: PayoutStatus) -> bool:
    if type(current) is not PayoutStatus or type(incoming) is not PayoutStatus:
        raise ValueError("Payout states must be typed enums")
    if current == incoming:
        return False
    if incoming not in _ALLOWED[current]:
        raise ValueError("Invalid payout state transition")
    return True
