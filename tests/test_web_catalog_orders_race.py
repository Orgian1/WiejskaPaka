"""Regression guards for overlapping catalog/order requests and account switching."""
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[1] / 'web' / 'app.js').read_text(encoding='utf-8')


def test_catalog_rejects_stale_responses_before_render():
    assert 'let productRequest = 0, orderRequest = 0' in SCRIPT
    assert "const request=++productRequest;const epoch=sessionEpoch;const products=await catalogPage(request,epoch);if(request!==productRequest||epoch!==sessionEpoch||products===null)return;clear('products');" in SCRIPT


def test_orders_reject_stale_responses_before_render():
    orders = SCRIPT.split('async function loadOrders(){', 1)[1].split('async function act(', 1)[0]
    guard = "const request=++orderRequest;const epoch=sessionEpoch;const orders=await api('/orders/me');if(request!==orderRequest||epoch!==sessionEpoch)return;"
    assert guard in orders
    # Every visible mutation must follow the same request and account guard.
    guard_end = orders.index(guard) + len(guard)
    assert orders.index('updateSellerOrderCount(orders)') >= guard_end
    assert orders.index("clear('orders');") >= guard_end
    assert orders.index("el('orders').append(") >= guard_end


def test_account_switch_invalidates_pending_catalog_and_order_refreshes():
    assert 'productRequest++;orderRequest++;role=' in SCRIPT
