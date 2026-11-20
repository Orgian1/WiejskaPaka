"""GPS arrival changes only eligible orders at the seller's own pickup point."""
from tests.test_postgres_full_api_optin import product, register
from tests.test_purchase_record_http_restart import server


NEAR = {'latitude_e6': 51_210_000, 'longitude_e6': 16_160_000, 'accuracy_m': 10}


def exercise_arrival(client, *, require_gps=False):
    seller, seller_id = register(client, 'rolnik')
    other_seller, _ = register(client, 'rolnik')
    buyer, _ = register(client, 'klient')
    other_buyer, _ = register(client, 'klient')
    place = {'name': 'Punkt testowy', 'city': 'Legnica', 'street': 'Polna 1',
             'opening_hours': '9-16', 'latitude_e6': NEAR['latitude_e6'],
             'longitude_e6': NEAR['longitude_e6']}
    point = client.post('/pickup-points', headers=seller, json=place).json()['id']
    other_point = client.post('/pickup-points', headers=seller, json={
        **place, 'name': 'Drugi punkt',
    }).json()['id']
    item = product(client, seller)

    def checkout(point_id):
        response = client.post('/orders', headers=buyer, json={
            'product_id': item, 'quantity': 2, 'fulfillment': 'odbior', 'pickup_point_id': point_id,
        })
        assert response.status_code == 201, response.text
        return response.json()

    receipt, second_receipt = checkout(point), checkout(point)
    other_receipt = checkout(other_point)
    route = f'/pickup-points/{point}/arrival'

    assert client.post(route, json=NEAR).status_code == 401
    assert client.post(route, headers=buyer, json=NEAR).status_code == 403
    assert client.post(route, headers=other_seller, json=NEAR).status_code == 404
    assert client.post(route, headers=seller, json={**NEAR, 'accuracy_m': 300}).status_code == 422
    assert client.post(route, headers=seller, json={**NEAR, 'latitude_e6': 51_220_000}).status_code == 422
    if require_gps:
        assert client.post(f'/test/orders/{receipt["id"]}/ready', headers=seller).status_code == 409

    def statuses():
        return {row['id']: row['status'] for row in client.get('/orders/me', headers=buyer).json()}

    assert set(statuses().values()) == {'oczekuje_na_platnosc_testowa'}
    result = client.post(route, headers=seller, json=NEAR)
    assert result.status_code == 200, result.text
    assert result.json()['notified_orders'] == 2
    arrival = next(p for p in client.get('/farmers/me/pickup-points', headers=seller).json() if p['id'] == point)
    assert arrival['last_arrival_at'] == result.json()['confirmed_at']
    assert all('last_arrival_at' not in p for p in client.get(f'/farmers/{seller_id}/pickup-points').json())
    assert statuses() == {
        receipt['id']: 'gotowe_do_odbioru_testowo',
        second_receipt['id']: 'gotowe_do_odbioru_testowo',
        other_receipt['id']: 'oczekuje_na_platnosc_testowa',
    }
    repeat = client.post(route, headers=seller, json=NEAR)
    assert repeat.status_code == 200
    assert repeat.json()['notified_orders'] == 0
    notices = [notice for notice in client.get('/notifications/me', headers=buyer).json()
               if notice['event_type'] == 'pickup_arrived']
    assert {notice['order_id'] for notice in notices} == {receipt['id'], second_receipt['id']}
    assert len(notices) == 2
    assert client.get('/notifications/me', headers=other_buyer).json() == []
    confirmed = client.post(f'/orders/{receipt["id"]}/confirm', headers=seller,
                            json={'pin': receipt['pin_test_only']})
    assert confirmed.status_code == 200 and confirmed.json()['confirmed']


def test_gps_arrival_sqlite(tmp_path, monkeypatch):
    monkeypatch.setenv('WP_REQUIRE_PICKUP_GPS', '1')
    with server(tmp_path/'arrival.sqlite3') as client:
        exercise_arrival(client, require_gps=True)
