import pytest
from backend.shipment_groups import build_shipment_plan


def item(pid, seller=1, qty=1, price=1000, fee=1500, key='default'):
    return dict(product_id=pid, farmer_id=seller, quantity=qty,
                price_grosze=price, delivery_grosze=fee, shipment_key=key)


def test_many_products_one_shipment_one_fee():
    plan = build_shipment_plan([item(i) for i in range(1, 31)], 'dostawa')
    assert len(plan) == 1
    assert plan[0]['delivery_grosze'] == 1500
    assert plan[0]['total_grosze'] == 31500


def test_separate_shipments_have_separate_fees():
    plan = build_shipment_plan([item(1, key='A'), item(2, key='B')], 'dostawa')
    assert len(plan) == 2
    assert sum(p['delivery_grosze'] for p in plan) == 3000


def test_two_sellers_two_shipments():
    plan = build_shipment_plan([item(1), item(2, seller=2)], 'dostawa')
    assert len(plan) == 2


def test_pickup_is_free():
    assert build_shipment_plan([item(1), item(2)], 'odbior')[0]['delivery_grosze'] == 0


def test_max_rate_once_not_sum():
    plan = build_shipment_plan([item(1, fee=800), item(2, fee=1200)], 'dostawa')
    assert plan[0]['delivery_grosze'] == 1200

@pytest.mark.parametrize('bad', [0, -1, 1.5, '100'])
def test_invalid_quantities(bad):
    with pytest.raises(ValueError):
        build_shipment_plan([item(1, qty=bad)], 'dostawa')


def test_overflow():
    with pytest.raises(ValueError):
        build_shipment_plan([item(1, qty=2, price=9223372036854775807)], 'dostawa')


def test_empty():
    assert build_shipment_plan([], 'dostawa') == []
