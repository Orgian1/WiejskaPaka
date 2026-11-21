"""Verify the approved demo features through real PostgreSQL and TCP HTTP."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from tests.test_postgres_full_api_optin import (
    _postgres_api, delivery, inspection_connect, pg_api, product, register,
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


def test_native_pickup_arrival(pg_api):
    from tests.test_pickup_arrival import exercise_arrival

    client, _ = pg_api
    exercise_arrival(client)


@pytest.fixture
def pg_starter_api():
    yield from _postgres_api(starter_promo_code='START-APPROVED', seventh_promo_code='SEVENTH-APPROVED')


def test_starter_code_only_for_eligible_sellers(pg_starter_api):
    client, parameters = pg_starter_api
    seller, _ = register(client, 'rolnik')
    existing_seller, _ = register(client, 'rolnik')
    buyer, _ = register(client, 'klient')
    admin, admin_id = register(client, 'klient')
    with inspection_connect(**parameters) as owner:
        owner.execute("UPDATE users SET role='admin' WHERE id=%s", (admin_id,))
    endpoint = '/farmers/me/pickup-promotions/starter'
    featured = '/farmers/me/pickup-promotions/featured'
    assert client.get(featured).status_code == 401
    assert client.get(featured, headers=buyer).status_code == 403
    assert client.get(endpoint).status_code == 401
    assert client.get(endpoint, headers=buyer).status_code == 403
    assert client.get(endpoint, headers=seller).json() == {'code': None}
    settings = {'expires_on': '2099-12-31', 'max_redemptions': 10}
    assert client.post('/admin/pickup-promotions', headers=admin, json={
        'code': 'START-APPROVED', **settings,
    }).status_code == 201
    product(client, existing_seller)
    assert client.get(endpoint, headers=existing_seller).json() == {'code': None}
    assert client.get(featured, headers=existing_seller).json() == {'code': 'START-APPROVED'}
    available = client.get(endpoint, headers=seller)
    assert available.headers['cache-control'] == 'no-store'
    assert available.json() == {'code': 'START-APPROVED'}
    assert client.post('/farmers/me/pickup-promotions/redeem', headers=seller,
                       json={'code': 'START-APPROVED'}).status_code == 201
    assert client.get(endpoint, headers=seller).json() == {'code': None}
    new_seller, _ = register(client, 'rolnik')
    assert client.put('/admin/pickup-promotions/START-APPROVED', headers=admin,
                      json={**settings, 'active': False}).status_code == 200
    assert client.get(endpoint, headers=new_seller).json() == {'code': None}
    assert client.get(featured, headers=new_seller).json() == {'code': None}


def test_seventh_point_promotion_tracks_six_currently_active_points(pg_starter_api):
    from datetime import timedelta

    client, parameters = pg_starter_api
    seller, seller_id = register(client, 'rolnik')
    admin, admin_id = register(client, 'klient')
    with inspection_connect(**parameters) as owner:
        owner.execute("UPDATE users SET role='admin' WHERE id=%s", (admin_id,))

    for code, kind in [('START-APPROVED', 'starter'), ('SEVENTH-APPROVED', 'seventh'),
                       ('SEVENTH-ROTATED', 'seventh')]:
        response = client.post('/admin/pickup-promotions', headers=admin, json={
            'code': code, 'kind': kind, 'expires_on': '2099-12-31', 'max_redemptions': 10,
        })
        assert response.status_code == 201, response.text

    featured = '/farmers/me/pickup-promotions/featured'
    redeem = '/farmers/me/pickup-promotions/redeem'
    start = {'code': 'START-APPROVED'}
    seventh = {'code': 'SEVENTH-APPROVED'}
    point = {'name': 'Punkt próbny', 'city': 'Opole', 'street': 'Polna 1', 'opening_hours': '9-16'}

    def add_point():
        response = client.post('/pickup-points', headers=seller, json=point)
        assert response.status_code == 201, response.text
        return response.json()

    assert client.get(featured, headers=seller).json() == start
    assert client.post(redeem, headers=seller, json=seventh).status_code == 409
    assert client.post(redeem, headers=seller, json=start).status_code == 201
    assert add_point()['promotion']
    assert add_point()['promotion']
    assert client.get(featured, headers=seller).json() == {'code': None}
    assert add_point()['promotion']
    assert client.get(featured, headers=seller).json() == {**seventh, 'kind': 'seventh'}

    response = client.post(redeem, headers=seller, json=seventh)
    assert response.status_code == 201 and response.json()['remaining'] == 1
    assert client.post(redeem, headers=seller, json={'code': 'SEVENTH-ROTATED'}).status_code == 409

    test_points = [add_point() for _ in range(4)]
    assert all(point['promotion'] is None for point in test_points)
    now = datetime.now(timezone.utc)
    with inspection_connect(**parameters) as owner:
        for index, record in enumerate(test_points):
            end = now + (timedelta(days=-1) if index == 3 else timedelta(days=2))
            owner.execute("""INSERT INTO pickup_point_periods
                (id,point_id,farmer_id,starts_at,ends_at,price_grosze,kind,wallet_entry_id)
                VALUES (%s,%s,%s,%s,%s,0,'promotion',NULL)""",
                (uuid4().hex,record['id'],seller_id,(now-timedelta(days=2)).isoformat(),end.isoformat()))
        owner.execute('UPDATE pickup_points SET active=0 WHERE id=%s', (test_points[2]['id'],))

    assert add_point()['promotion'] is None
    reactivated = client.put(f"/pickup-points/{test_points[2]['id']}", headers=seller,
                             json={**point, 'active': True})
    assert reactivated.status_code == 200, reactivated.text
    with ThreadPoolExecutor(2) as pool:
        candidates = list(pool.map(lambda _: add_point(), range(2)))
    winners = [point for point in candidates if point['promotion']]
    assert len(winners) == 1
    end = datetime.fromisoformat(winners[0]['promotion']['free_until'])
    assert now <= end - timedelta(days=30) <= datetime.now(timezone.utc)
    assert client.post(redeem, headers=seller, json=seventh).json()['remaining'] == 0
