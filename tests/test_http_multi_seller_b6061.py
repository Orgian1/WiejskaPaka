"""Actual HTTP integration for mixed products, multiple farmers and shipment fees."""
from scripts.check_http_multi_seller_cart import run


def test_http_multi_seller_cart_and_idempotency():
    result = run()
    assert result['status'] == 'PASS'
    assert result['passed'] >= 30
    for label in ('two sellers: one maximum delivery charge per seller',
                  'seller A two different products, one 699 grosze shipping',
                  'idempotency prevents duplicate shipment',
                  'sum of two separate shipments matches basket quote',
                  'shipment details retain single shipping fee'):
        assert label in result['checks']
