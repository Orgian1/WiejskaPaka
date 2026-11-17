"""Pure payout review policy; no transfer is ever executed here."""
from dataclasses import dataclass
from backend.payu_preparation import seller_withdrawal_split, customer_withdrawal_split


@dataclass(frozen=True)
class PayoutReview:
    role: str
    requested_grosze: int
    available_grosze: int
    net_grosze: int
    fee_grosze: int


def review_payout(role: str, requested_grosze: int, available_grosze: int) -> PayoutReview:
    if role not in ("klient", "rolnik"):
        raise ValueError("Unknown wallet role")
    if type(requested_grosze) is not int or requested_grosze <= 0:
        raise ValueError("Requested amount must be positive integer grosze")
    if type(available_grosze) is not int or available_grosze < 0:
        raise ValueError("Available amount must be nonnegative integer grosze")
    if requested_grosze > available_grosze:
        raise ValueError("Insufficient wallet funds")
    net, fee = (seller_withdrawal_split(requested_grosze)
                if role == "rolnik" else customer_withdrawal_split(requested_grosze))
    return PayoutReview(role, requested_grosze, available_grosze, net, fee)
