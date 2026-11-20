"""Verify the approved demo features through real PostgreSQL and TCP HTTP."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

from tests.test_postgres_full_api_optin import (
    delivery, inspection_connect, pg_api, product, register,
)
from tests.test_wallet_ads_http import campaign, claim


def test_native_approved_ads_and_rating(pg_api):
    client, parameters = pg_api
    buyer, _ = register(client, 'klient')
    other, _ = register(client, 'klient')
    seller, seller_id = register(client, 'rolnik')
    admin, admin_id = register(client, 'klient')
    with inspection_connect(**parameters) as owner:
        owner.execute("UPDATE users SET role='admin' WHERE id=%s", (admin_id,))

    ads = {}
    for role in ('klient', 'rolnik'):
        response = client.post('/admin/wallet-ads', headers=admin, json=campaign(audience=role))
        assert response.status_code == 201, response.text
        ads[role] = response.json()['id']

    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(lambda _: claim(client, buyer), range(2)))
    assert all(r.status_code == 200 for r in responses)
    shown = [r.json()['ad'] for r in responses if r.json()['ad']]
    assert len(shown) == 1
    assert shown[0]['id'] == ads['klient'] and shown[0]['duration_seconds'] == 5
    assert claim(client, seller).json()['ad']['id'] == ads['rolnik']
    click = f"/wallet/ads/impressions/{shown[0]['impression_id']}/click"
    assert client.post(click, headers=other).status_code == 404
    assert client.post(click, headers=buyer).status_code == 200
    assert client.get('/admin/wallet-ads', headers=buyer).status_code == 403

    now = int(datetime.now(timezone.utc).timestamp())
    response = client.post('/admin/ads/slots', headers=admin, json={
        'slot': 'login', 'title': 'Kod dla sprzedawców', 'body': 'Trzy punkty',
        'enabled': True, 'starts_at': now - 60, 'ends_at': now + 60,
    })
    assert response.status_code == 201
    assert client.get('/ads/slots/login').json()['campaign']['id'] == response.json()['id']
    assert client.get('/ads/slots/buyer').json() == {'campaign': None}
    assert client.get('/admin/ads/slots', headers=buyer).status_code == 403

    item = product(client, seller)
    checkout = client.post('/orders', headers=buyer, json=delivery(item))
    assert checkout.status_code == 201, checkout.text
    order_id = checkout.json()['id']
    rating = {'order_id': order_id, 'stars': 5}
    assert client.post('/seller-ratings', headers=other, json=rating).status_code == 404
    assert client.post('/seller-ratings', headers=buyer, json=rating).status_code == 409
    # Set a completed-order fixture independently of the rating endpoint.
    with inspection_connect(**parameters) as owner:
        owner.execute("""UPDATE orders SET status='odebrane',pin_used=1,confirmed_at=%s
                         WHERE id=%s""", (datetime.now(timezone.utc).isoformat(), order_id))
    assert client.post('/seller-ratings', headers=buyer, json=rating).status_code == 201
    assert client.post('/seller-ratings', headers=buyer, json=rating).status_code == 409
    assert client.get(f'/seller-ratings/orders/{order_id}', headers=other).status_code == 404
    assert client.get(f'/sellers/{seller_id}/rating').json() == {
        'seller_id': seller_id, 'count': 1, 'average': 5.0,
    }


def test_native_promotion_period_visible_and_private(pg_api):
    client, parameters = pg_api
    seller, seller_id = register(client, 'rolnik')
    other, _ = register(client, 'rolnik')
    admin, admin_id = register(client, 'klient')
    with inspection_connect(**parameters) as owner:
        owner.execute("UPDATE users SET role='admin' WHERE id=%s", (admin_id,))
    code = 'DEMO-' + uuid4().hex.upper()
    assert client.post('/admin/pickup-promotions', headers=admin, json={
        'code': code, 'expires_on': '2099-12-31', 'max_redemptions': 1,
    }).status_code == 201
    assert client.post('/farmers/me/pickup-promotions/redeem', headers=seller,
                       json={'code': code}).status_code == 201
    point = client.post('/pickup-points', headers=seller, json={
        'name': 'Punkt testowy', 'city': 'Opole', 'street': 'Polna 1', 'opening_hours': '9-16',
    })
    assert point.status_code == 201, point.text
    point_id = point.json()['id']
    quote = f'/farmers/me/pickup-points/{point_id}/renewal-quote'
    assert client.get(quote, headers=other).status_code == 404
    details = client.get(quote, headers=seller).json()
    assert details['entitled'] and details['period']['price_grosze'] == 0
    assert details['renewal']['price_grosze'] == 1000
    start = datetime.fromisoformat(details['period']['starts_at'])
    end = datetime.fromisoformat(details['period']['ends_at'])
    assert (end.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds() == 30 * 86400
    assert [row['id'] for row in client.get(f'/farmers/{seller_id}/pickup-points').json()] == [point_id]
    with inspection_connect(**parameters) as owner:
        owner.execute("UPDATE pickup_point_periods SET ends_at='2000-01-01T00:00:00Z' WHERE point_id=%s",
                      (point_id,))
    assert client.get(f'/farmers/{seller_id}/pickup-points').json() == []
    buyer, _ = register(client, 'klient')
    item = product(client, seller)
    pickup = {'fulfillment': 'odbior', 'pickup_point_id': point_id}
    assert client.put('/cart/items', headers=buyer, json={'product_id': item, 'quantity': 1}).status_code == 200
    assert client.post('/cart/checkout-test', headers=buyer, json=pickup).status_code == 422
    assert client.post('/orders', headers=buyer, json={
        **pickup, 'product_id': item, 'quantity': 1,
    }).status_code == 422
