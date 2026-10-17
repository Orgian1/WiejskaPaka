"""Samodzielne demo API na jednorazowej SQLite. Nie uruchamia płatności ani Neon."""
import os
import sys
import tempfile
from pathlib import Path


def main():
    # Konfigurację ustawiamy przed importem aplikacji.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    for key in ('DATABASE_URL', 'WP_TEST_DATABASE_URL', 'WP_TEST_POSTGRES_DSN',
                'WP_ALLOW_REMOTE_DISPOSABLE_TEST_DB'):
        os.environ.pop(key, None)
    with tempfile.TemporaryDirectory(prefix='wiejskapaka_demo_') as folder:
        os.environ['WIEJSKAPAKA_DB'] = str(Path(folder) / 'demo.sqlite3')
        from fastapi.testclient import TestClient
        from backend.app import app
        client = TestClient(app)

        def request(method, path, expected, *, headers=None, json=None):
            result = client.request(method, path, headers=headers, json=json)
            if result.status_code != expected:
                raise AssertionError(f'{method} {path}: {result.status_code} (oczekiwano {expected}): {result.text[:300]}')
            return result.json()

        def account(role):
            email = f'demo-{role}@example.invalid'
            credentials = {'email': email, 'password': 'TestoweHaslo_123456789'}
            request('POST', '/auth/register', 201, json={**credentials, 'role': role})
            login = request('POST', '/auth/login', 200, json=credentials)
            return {'Authorization': 'Bearer ' + login['access_token']}

        farmer, buyer, courier = (account(role) for role in ('rolnik', 'klient', 'dostawca'))
        product = request('POST', '/products', 201, headers=farmer,
                          json={'name': 'Marchew demo', 'price_grosze': 349,
                                'delivery_grosze': 501, 'stock': 3})
        point = request('POST', '/pickup-points', 201, headers=farmer,
                        json={'name': 'Punkt demo', 'city': 'Radom',
                              'street': 'Polna 2', 'opening_hours': '8-16'})
        pickup = request('POST', '/orders', 201, headers=buyer,
                         json={'product_id': product['id'], 'quantity': 1,
                               'fulfillment': 'odbior', 'pickup_point_id': point['id']})
        assert pickup['total_grosze'] == 349
        request('POST', f"/test/orders/{pickup['id']}/ready", 200, headers=farmer)
        assert request('POST', f"/orders/{pickup['id']}/confirm", 200, headers=farmer,
                       json={'pin': pickup['pin_test_only'], 'checked_goods': True})['confirmed']
        request('POST', f"/orders/{pickup['id']}/confirm", 409, headers=farmer,
                json={'pin': pickup['pin_test_only'], 'checked_goods': True})
        delivery = request('POST', '/orders', 201, headers=buyer,
                           json={'product_id': product['id'], 'quantity': 1,
                                 'fulfillment': 'dostawa', 'delivery_city': 'Radom',
                                 'delivery_street': 'Leśna 4', 'delivery_postal_code': '26-600'})
        assert delivery['total_grosze'] == 850
        oid = delivery['id']
        courier_id = request('GET', '/auth/me', 200, headers=courier)['id']
        request('POST', f'/orders/{oid}/assign-courier-test', 200, headers=farmer,
                json={'courier_id': courier_id})
        request('GET', f'/orders/{oid}/location', 403, headers=courier)
        request('POST', f'/orders/{oid}/dispatch-test', 200, headers=farmer)
        request('GET', f'/orders/{oid}/location', 200, headers=courier)
        request('POST', f'/orders/{oid}/confirm', 403, headers=buyer,
                json={'pin': delivery['pin_test_only'], 'checked_goods': True})
        assert request('POST', f'/orders/{oid}/confirm', 200, headers=courier,
                       json={'pin': delivery['pin_test_only'], 'checked_goods': True})['confirmed']
        request('GET', f'/orders/{oid}/location', 403, headers=courier)
        orders = request('GET', '/orders/me', 200, headers=buyer)
        assert {pickup['id'], delivery['id']} <= {o['id'] for o in orders if o['status'] == 'odebrane'}
        print('DEMO OK: odbiór, dostawa, PIN jednorazowy, prywatność adresu, kwoty w groszach.')
        print('Dane demonstracyjne usunięte; bez Neon i prawdziwych płatności.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
