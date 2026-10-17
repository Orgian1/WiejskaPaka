import pytest
from backend.settlement_preview import calculate


def test_split_exact():
    x = calculate(9999, 1200, 500)
    assert x['commission_grosze'] == 500
    assert x['seller_amount_grosze'] == 10699
    assert x['seller_amount_grosze'] + x['commission_grosze'] == x['customer_total_grosze'] == 11199
    assert x['payment_captured'] is False and x['payout_scheduled'] is False


def test_small_amount_rounding():
    x = calculate(1, 0, 500)
    assert x['commission_grosze'] == 0
    assert x['seller_amount_grosze'] == 1

@pytest.mark.parametrize('amount,delivery,rate', [(-1,0,500),(1,-1,500),(1,0,10001),(True,0,500),(1,0,2.5),(9_000_000_000_000,1,0)])
def test_reject_invalid(amount,delivery,rate):
    with pytest.raises(ValueError):
        calculate(amount,delivery,rate)
