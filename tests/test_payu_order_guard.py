import pytest

from backend.payu_order_guard import validate_provider_order


def valid(**changes):
    args = dict(expected_order_id="order-1", expected_amount_grosze=1099,
                expected_currency="PLN", received_order_id="order-1",
                received_amount_grosze=1099, received_currency="PLN")
    args.update(changes)
    return args


def test_exact_provider_order_amount_and_currency():
    assert validate_provider_order(**valid()) is None


@pytest.mark.parametrize("changes", [
    {"received_order_id":"order-2"},
    {"received_amount_grosze":1098},
    {"received_amount_grosze":1099.0},
    {"received_amount_grosze":True},
    {"received_currency":"EUR"},
    {"expected_currency":"EUR"},
    {"expected_amount_grosze":0},
])
def test_reject_mismatched_order(changes):
    with pytest.raises(ValueError):
        validate_provider_order(**valid(**changes))
