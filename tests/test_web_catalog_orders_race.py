"""Regression guards for overlapping catalog/order requests and account switching."""
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[1] / 'web' / 'app.js').read_text(encoding='utf-8')


def test_catalog_rejects_stale_responses_before_render():
    assert 'let productRequest = 0, orderRequest = 0' in SCRIPT
    assert "const request=++productRequest;const epoch=sessionEpoch;const products=await api('/products');if(request!==productRequest||epoch!==sessionEpoch)return;clear('products');" in SCRIPT


def test_orders_reject_stale_responses_before_render():
    assert "const request=++orderRequest;const epoch=sessionEpoch;const orders=await api('/orders/me');if(request!==orderRequest||epoch!==sessionEpoch)return;clear('orders');" in SCRIPT


def test_account_switch_invalidates_pending_catalog_and_order_refreshes():
    assert 'productRequest++;orderRequest++;role=' in SCRIPT
