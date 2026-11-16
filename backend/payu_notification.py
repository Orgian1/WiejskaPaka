"""Review-only PayU callback mapping.

A caller must authenticate provider notifications independently before invoking
this mapper. Never trust this mapper alone to credit a wallet.
"""
from backend.payu_preparation import PaymentStatus


PAYU_STATUS_MAP = {
    "PENDING": PaymentStatus.PENDING,
    "WAITING_FOR_CONFIRMATION": PaymentStatus.PENDING,
    "COMPLETED": PaymentStatus.CONFIRMED,
    "CANCELED": PaymentStatus.CANCELLED,
}


def parse_payu_order_notification(payload: dict) -> tuple[str, PaymentStatus]:
    if not isinstance(payload, dict) or not isinstance(payload.get("order"), dict):
        raise ValueError("Malformed PayU order notification")
    order = payload["order"]
    order_id = order.get("orderId")
    status = order.get("status")
    if not isinstance(order_id, str) or not order_id or len(order_id) > 120:
        raise ValueError("Invalid PayU order identifier")
    if not isinstance(status, str) or status not in PAYU_STATUS_MAP:
        raise ValueError("Unknown PayU payment status")
    return order_id, PAYU_STATUS_MAP[status]
