"""PayU-ready, provider-neutral payment preparation. No live PayU credentials or API calls.

This module deliberately does not modify the wallet balance. A separate, reviewed
ledger integration must consume verified events transactionally and idempotently.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class PaymentStatus(str, Enum):
    CREATED = "CREATED"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


@dataclass(frozen=True)
class PaymentRequest:
    operation_id: str
    user_id: int
    amount_grosze: int
    currency: str = "PLN"

    def __post_init__(self):
        if not self.operation_id or not isinstance(self.operation_id, str) or len(self.operation_id) > 120:
            raise ValueError("operation_id is required")
        if type(self.user_id) is not int or self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if type(self.amount_grosze) is not int or self.amount_grosze <= 0:
            raise ValueError("amount_grosze must be a positive integer")
        if self.currency != "PLN":
            raise ValueError("Only PLN is supported")


@dataclass(frozen=True)
class PaymentResult:
    operation_id: str
    provider_order_id: str
    status: PaymentStatus
    redirect_url: str | None = None


class PaymentProvider(Protocol):
    def create_topup(self, request: PaymentRequest) -> PaymentResult: ...
    def get_payment_status(self, provider_order_id: str) -> PaymentStatus: ...
    def request_refund(self, provider_order_id: str, amount_grosze: int, refund_id: str) -> str: ...


class PayUNotConfigured(RuntimeError):
    pass


class PayUDisabledAdapter:
    """Safe default: prevents accidental real payment initiation."""

    def create_topup(self, request: PaymentRequest) -> PaymentResult:
        raise PayUNotConfigured("PayU has not been configured or verified")

    def get_payment_status(self, provider_order_id: str) -> PaymentStatus:
        raise PayUNotConfigured("PayU has not been configured or verified")

    def request_refund(self, provider_order_id: str, amount_grosze: int, refund_id: str) -> str:
        raise PayUNotConfigured("PayU has not been configured or verified")


class SimulatedPaymentProvider:
    """In-memory test double. Never use as evidence of actual payment.

    It does not expose an unverified callback endpoint and cannot credit a wallet.
    """
    def __init__(self):
        self._payments: dict[str, PaymentResult] = {}
        self._requests: dict[str, PaymentRequest] = {}
        self._refunds: dict[str, tuple[str, int]] = {}
        self._refunded_grosze: dict[str, int] = {}

    def create_topup(self, request: PaymentRequest) -> PaymentResult:
        existing = self._payments.get(request.operation_id)
        if existing is not None:
            if self._requests[request.operation_id] != request:
                raise ValueError('Operation id reused with different payment details')
            return existing
        result = PaymentResult(request.operation_id, "SIM-" + request.operation_id,
                               PaymentStatus.PENDING)
        self._payments[request.operation_id] = result
        self._requests[request.operation_id] = request
        return result

    def get_payment_status(self, provider_order_id: str) -> PaymentStatus:
        for payment in self._payments.values():
            if payment.provider_order_id == provider_order_id:
                return payment.status
        raise KeyError("Unknown simulated payment")

    def set_test_status(self, operation_id: str, status: PaymentStatus):
        if type(status) is not PaymentStatus or status not in (PaymentStatus.CONFIRMED, PaymentStatus.FAILED,
                          PaymentStatus.CANCELLED):
            raise ValueError("Unsupported test status")
        existing = self._payments[operation_id]
        if existing.status != PaymentStatus.PENDING:
            raise ValueError("Terminal status cannot be overwritten")
        self._payments[operation_id] = PaymentResult(existing.operation_id,
                                                     existing.provider_order_id, status)

    def request_refund(self, provider_order_id: str, amount_grosze: int, refund_id: str) -> str:
        if type(amount_grosze) is not int or amount_grosze <= 0 or not isinstance(refund_id, str) or not refund_id or len(refund_id) > 120:
            raise ValueError("Invalid refund")
        if self.get_payment_status(provider_order_id) != PaymentStatus.CONFIRMED:
            raise ValueError("Payment is not confirmed")
        existing = self._refunds.get(refund_id)
        if existing is not None:
            if existing != (provider_order_id, amount_grosze):
                raise ValueError('Refund id reused with different details')
            return refund_id
        operation_id = next((key for key, payment in self._payments.items()
                             if payment.provider_order_id == provider_order_id), None)
        if operation_id is None:
            raise KeyError('Unknown simulated payment')
        already_refunded = self._refunded_grosze.get(provider_order_id, 0)
        if already_refunded + amount_grosze > self._requests[operation_id].amount_grosze:
            raise ValueError('Refund exceeds original payment')
        self._refunds[refund_id] = (provider_order_id, amount_grosze)
        self._refunded_grosze[provider_order_id] = already_refunded + amount_grosze
        return refund_id


def seller_withdrawal_split(gross_grosze: int) -> tuple[int, int]:
    """5% platform commission, half-up to nearest grosz, seller receives remainder."""
    if type(gross_grosze) is not int or gross_grosze <= 0:
        raise ValueError("gross_grosze must be positive integer")
    fee = (gross_grosze * 5 + 50) // 100
    return gross_grosze - fee, fee


def customer_withdrawal_split(gross_grosze: int) -> tuple[int, int]:
    if type(gross_grosze) is not int or gross_grosze <= 0:
        raise ValueError("gross_grosze must be positive integer")
    return gross_grosze, 0


class PayoutStatus(str, Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    SENT = "SENT"
    SETTLED = "SETTLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class PayoutRequest:
    payout_id: str
    user_id: int
    role: str
    gross_grosze: int

    def __post_init__(self):
        if not self.payout_id or not isinstance(self.payout_id, str) or len(self.payout_id) > 120:
            raise ValueError("payout_id is required")
        if type(self.user_id) is not int or self.user_id <= 0:
            raise ValueError("Invalid user")
        if self.role not in ("klient", "rolnik"):
            raise ValueError("Unsupported payout role")
        if type(self.gross_grosze) is not int or self.gross_grosze <= 0:
            raise ValueError("Payout amount must be positive integer")

    @property
    def net_and_fee(self) -> tuple[int, int]:
        if self.role == "rolnik":
            return seller_withdrawal_split(self.gross_grosze)
        return customer_withdrawal_split(self.gross_grosze)


class PayoutProvider(Protocol):
    def submit_payout(self, request: PayoutRequest) -> PayoutStatus: ...
    def get_payout_status(self, payout_id: str) -> PayoutStatus: ...


class DisabledPayoutProvider:
    """No production payout method until operator contract and KYC are verified."""
    def submit_payout(self, request: PayoutRequest) -> PayoutStatus:
        raise PayUNotConfigured("Payouts require an approved operator agreement")

    def get_payout_status(self, payout_id: str) -> PayoutStatus:
        raise PayUNotConfigured("Payouts require an approved operator agreement")
