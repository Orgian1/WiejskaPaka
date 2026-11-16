import pytest
from backend.payu_payout_review import review_payout


def test_seller_payout_fee_is_five_percent_in_grosze():
    result = review_payout("rolnik", 10001, 15000)
    assert result.net_grosze + result.fee_grosze == 10001
    assert result.fee_grosze == 500


def test_customer_payout_has_no_platform_fee():
    result = review_payout("klient", 10001, 15000)
    assert result.net_grosze == 10001
    assert result.fee_grosze == 0


@pytest.mark.parametrize("role,requested,available", [
    ("admin",100,100), ("klient",101,100), ("rolnik",0,100),
    ("rolnik",1.0,100), ("rolnik",1,True), ("rolnik",1,-1),
])
def test_reject_invalid_payout(role, requested, available):
    with pytest.raises(ValueError):
        review_payout(role,requested,available)
