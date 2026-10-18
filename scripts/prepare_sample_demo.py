"""Create synthetic role accounts and shipments only in a new private directory.

Run in a fresh child process; never opens or upgrades an existing database.
Credentials are returned only to the local launcher, not stored in a report.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_phone_demo import demo_environment


def prepare(directory):
    if 'backend.app' in sys.modules:
        raise ValueError('Wymagany nowy proces')
    directory = Path(directory).absolute()
    # Atomic mkdir refuses even an existing empty directory or a symlink.
    directory.mkdir(mode=0o700)
    previous_mask = os.umask(0o077)
    try:
        database = directory/'demo.sqlite3'
        env = demo_environment(os.environ, database)
        env['WP_ENABLE_TEST_PAYMENTS'] = '1'
        os.environ.clear()
        os.environ.update(env)
        from fastapi.testclient import TestClient
        from backend.app import app, db, ph
        from backend.seller_compliance import RULES_VERSION
        from backend.payment_integrity import audit_payment_integrity
        credentials, headers, users = {}, {}, {}
        with TestClient(app) as client:
            def request(method, path, expected=200, *, actor=None, body=None, extra=None):
                result = client.request(method, path, json=body,
                    headers={**(headers.get(actor, {}) if actor else {}), **(extra or {})})
                if result.status_code != expected:
                    raise ValueError('Nie można przygotować scenariusza testowego')
                return result.json()
            suffix = secrets.token_hex(6)
            for role in ('rolnik', 'klient', 'dostawca', 'admin'):
                credentials[role] = {'email': f'demo-{role}-{suffix}@example.invalid',
                                     'password': secrets.token_urlsafe(24)}
                if role == 'admin':
                    # This local-only path is unreachable through HTTP registration.
                    with db() as con:
                        row = con.execute('INSERT INTO users(email,password_hash,role) VALUES(?,?,?)',
                            (credentials[role]['email'], ph.hash(credentials[role]['password']), role))
                        users[role] = row.lastrowid
                else:
                    users[role] = request('POST', '/auth/register', 201,
                        body={**credentials[role], 'role': role})['id']
                login = request('POST', '/auth/login', body=credentials[role])
                headers[role] = {'Authorization': 'Bearer '+login['access_token']}
            request('PUT', '/farmers/me/profile', actor='rolnik', body={
                'farm_name': 'Gospodarstwo demonstracyjne', 'city': 'Legnica',
                'description': 'Fikcyjna oferta do sprawdzania aplikacji.'})
            request('POST', '/farmers/me/compliance/acknowledge', actor='rolnik',
                    body={'rules_version': RULES_VERSION, 'accepted': True})
            point = request('POST', '/pickup-points', 201, actor='rolnik', body={
                'name': 'Punkt demonstracyjny', 'city': 'Legnica', 'street': 'Testowa 1',
                'opening_hours': 'Pon–Pt 9:00–17:00',
                'latitude_e6': 51_210_000, 'longitude_e6': 16_160_000})['id']
            products = []
            for name, price in (('Marchew demonstracyjna', 349), ('Ziemniaki demonstracyjne', 299)):
                products.append(request('POST', '/products', 201, actor='rolnik', body={
                    'name': name, 'price_grosze': price, 'delivery_grosze': 501, 'stock': 30})['id'])
            for fulfillment in ('odbior', 'dostawa'):
                for product in products:
                    request('PUT', '/cart/items', actor='klient', body={'product_id': product, 'quantity': 1})
                body = {'fulfillment': fulfillment}
                if fulfillment == 'odbior':
                    body['pickup_point_id'] = point
                else:
                    body.update(delivery_city='Legnica', delivery_street='Adres testowy 99', delivery_postal_code='59-220')
                receipt = request('POST', '/cart/checkout-test', 201, actor='klient', body=body,
                    extra={'Idempotency-Key': secrets.token_hex(20)})
                for order in receipt['orders']:
                    request('POST', f'/test/payments/{order["id"]}/events', actor='klient',
                        body={'event_id': secrets.token_hex(20), 'event_type': 'payment_success_test'})
                    if fulfillment == 'odbior':
                        request('POST', f'/test/orders/{order["id"]}/ready', actor='rolnik')
                if fulfillment == 'dostawa':
                    sid = receipt['shipment_id']
                    request('POST', f'/shipments/{sid}/assign-courier-test', actor='rolnik',
                        body={'courier_id': users['dostawca']})
                    request('POST', f'/shipments/{sid}/dispatch-test', actor='rolnik')
                if receipt['delivery_grosze'] != (501 if fulfillment == 'dostawa' else 0):
                    raise ValueError('Nieprawidłowa opłata demonstracyjna')
            with db() as con:
                audit = audit_payment_integrity(con)
                if not audit['ok'] or audit['checked_payments'] != 4:
                    raise ValueError('Nieprawidłowe płatności testowe')
                # No unowned sessions from setup remain after seeding.
                con.execute('DELETE FROM sessions')
        return {'database': str(database), 'credentials': credentials,
                'summary': {'users': 4, 'products': 2, 'shipments': 2, 'orders': 4,
                            'payments_checked': 4, 'delivery_grosze': 501}}
    except BaseException:
        shutil.rmtree(directory)
        raise
    finally:
        os.umask(previous_mask)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare(args.directory)
    except Exception:
        print('Nie udało się przygotować jednorazowego demo. Wymagany nowy katalog i nowy proces.', file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
