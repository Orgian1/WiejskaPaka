import pytest

from backend.payu_preparation import PaymentStatus
from backend.payu_notification import parse_payu_order_notification


@pytest.mark.parametrize("provider_status,expected", [
    ("PENDING",PaymentStatus.PENDING),
    ("WAITING_FOR_CONFIRMATION",PaymentStatus.PENDING),
    ("COMPLETED",PaymentStatus.CONFIRMED),
    ("CANCELED",PaymentStatus.CANCELLED),
])
def test_payu_status_mapping(provider_status, expected):
    assert parse_payu_order_notification({
        "order":{"orderId":"provider-order-1","status":provider_status}
    }) == ("provider-order-1", expected)


@pytest.mark.parametrize("payload", [{}, {"order":{}}, {"order":{"orderId":"1","status":"UNKNOWN"}},
                                     {"order":{"orderId":"","status":"COMPLETED"}}])
def test_invalid_payu_notification_rejected(payload):
    with pytest.raises(ValueError):
        parse_payu_order_notification(payload)
