"""Validate reconciliation of provider callbacks against a local payment order.

This guard is NOT a webhook authenticity verifier. Caller must independently
verify PayU origin and fetch provider status before any wallet posting.
"""


def validate_provider_order(*, expected_order_id: str, expected_amount_grosze: int,
                            expected_currency: str, received_order_id: str,
                            received_amount_grosze: int, received_currency: str) -> None:
    if not isinstance(expected_order_id, str) or not expected_order_id:
        raise ValueError("Expected provider order ID required")
    if type(expected_amount_grosze) is not int or expected_amount_grosze <= 0:
        raise ValueError("Expected amount must be positive integer grosze")
    if expected_currency != "PLN":
        raise ValueError("Unsupported currency")
    if not isinstance(received_order_id, str) or received_order_id != expected_order_id:
        raise ValueError("Provider order ID mismatch")
    if type(received_amount_grosze) is not int or received_amount_grosze != expected_amount_grosze:
        raise ValueError("Provider payment amount mismatch")
    if received_currency != expected_currency:
        raise ValueError("Provider currency mismatch")
