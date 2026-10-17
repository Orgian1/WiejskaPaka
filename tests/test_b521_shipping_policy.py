from backend.shipping_policy import shipment_fees
import pytest


def test_one_shipment_many_products_one_fee():
    items = [{'farmer_id': 7, 'delivery_grosze': v} for v in (800, 1200, 1000, 1200)]
    assert shipment_fees(items, 'dostawa') == {7: 1200}


def test_separate_sellers_separate_shipments():
    items = [{'farmer_id': 7, 'delivery_grosze': 1200},
             {'farmer_id': 8, 'delivery_grosze': 900}]
    assert shipment_fees(items, 'dostawa') == {7: 1200, 8: 900}
    assert shipment_fees(items, 'odbior') == {7: 0, 8: 0}


def test_invalid_fee_rejected():
    with pytest.raises(ValueError):
        shipment_fees([{'farmer_id': 1, 'delivery_grosze': -1}], 'dostawa')
    with pytest.raises(ValueError):
        shipment_fees([{'farmer_id': 1, 'delivery_grosze': 1.5}], 'dostawa')
