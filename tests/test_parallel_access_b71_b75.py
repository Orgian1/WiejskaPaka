"""B/71–75: równoległe zakupy i izolacja autoryzacji (SQLite/test API)."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app import app


def setup_case(stock=1):
    client = TestClient(app)
    suffix = uuid4().hex
    def user(role):
        email = f'b75-{role}-{uuid4().hex}@example.test'
        data = {'email': email, 'password': 'mocne-haslo-2026-test', 'role': role}
        assert client.post('/auth/register', json=data).status_code == 201
        response = client.post('/auth/login', json={'email': email, 'password': data['password']})
        assert response.status_code == 200
        return {'Authorization': 'Bearer ' + response.json()['access_token']}
    farmer, buyer1, buyer2, courier = user('rolnik'), user('klient'), user('klient'), user('dostawca')
    product = client.post('/products', headers=farmer, json={'name': 'Partia '+suffix, 'price_grosze': 349, 'delivery_grosze': 501, 'stock': stock})
    assert product.status_code == 201, product.text
    point = client.post('/pickup-points', headers=farmer, json={'name':'Punkt', 'city':'Radom', 'street':'Polna 1', 'opening_hours':'8-16'})
    assert point.status_code == 201, point.text
    payload = {'product_id': product.json()['id'], 'quantity': 1, 'fulfillment':'odbior', 'pickup_point_id': point.json()['id']}
    return client, farmer, buyer1, buyer2, courier, payload


def test_b71_parallel_purchase_one_remaining_item():
    c, farmer, a, b, courier, payload = setup_case()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda h: c.post('/orders', json=payload, headers=h), (a, b)))
    assert sorted(x.status_code for x in results) == [201, 409], [x.text for x in results]


def test_b72_parallel_purchase_distinct_stock_items():
    c, farmer, a, b, courier, payload = setup_case(stock=2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda h: c.post('/orders', json=payload, headers=h), (a, b)))
    assert [x.status_code for x in results] == [201, 201], [x.text for x in results]
    assert results[0].json()['id'] != results[1].json()['id']


def test_b73_parallel_replay_cannot_create_extra_order():
    c, farmer, a, b, courier, payload = setup_case(stock=1)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: c.post('/orders', json=payload, headers=a), range(4)))
    assert sum(r.status_code == 201 for r in results) == 1, [r.text for r in results]
    assert all(r.status_code in (201, 409) for r in results)


def test_b74_wrong_role_cannot_order_during_parallel_requests():
    c, farmer, a, b, courier, payload = setup_case(stock=2)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda h: c.post('/orders', json=payload, headers=h), (farmer, courier, a)))
    assert [r.status_code for r in results] == [403, 403, 201], [r.text for r in results]


def test_b75_other_account_cannot_access_order_after_concurrent_buy():
    c, farmer, a, b, courier, payload = setup_case()
    created = c.post('/orders', json=payload, headers=a)
    assert created.status_code == 201
    oid = created.json()['id']
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda path: c.get(path, headers=b), (f'/orders/{oid}/location', f'/orders/{oid}/events', '/orders/me')))
    assert responses[0].status_code == 403
    assert responses[1].status_code == 403
    assert responses[2].status_code == 200
    assert all(order['id'] != oid for order in responses[2].json())
