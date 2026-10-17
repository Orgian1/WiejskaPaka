"""Regression: cancelled orders restore inventory once, never on retries."""
from tests.test_api import c, reg


def test_cancel_twice_never_inflates_inventory():
    farmer = reg('cas-farmer-20261015@example.com', 'rolnik')
    buyer = reg('cas-buyer-20261015@example.com', 'klient')
    pid = c.post('/products', json={
        'name': 'Marchew CAS', 'price_grosze': 250,
        'delivery_grosze': 1, 'stock': 5,
    }, headers=farmer).json()['id']
    order = c.post('/orders', json={
        'product_id': pid, 'quantity': 4, 'fulfillment': 'dostawa',
        'delivery_city': 'Radom', 'delivery_street': 'Polna 7',
        'delivery_postal_code': '26-600',
    }, headers=buyer).json()
    assert next(p for p in c.get('/products').json() if p['id'] == pid)['stock'] == 1
    first = c.post(f'/orders/{order["id"]}/cancel-test', headers=buyer)
    second = c.post(f'/orders/{order["id"]}/cancel-test', headers=buyer)
    assert first.status_code == 200
    assert second.status_code == 409
    assert next(p for p in c.get('/products').json() if p['id'] == pid)['stock'] == 5


def test_cancel_compare_and_set_requires_pending_status():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / 'backend' / 'app.py').read_text()
    assert "WHERE id=? AND buyer_id=? AND status=?" in source
    assert 'if changed.rowcount != 1:' in source
