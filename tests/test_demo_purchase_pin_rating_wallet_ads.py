"""Combined demo flow: paid test purchase -> PIN collection -> rating -> wallet ad.

Runs against disposable SQLite only. No real payments or production data.
"""
from contextlib import closing
from datetime import datetime, timedelta, timezone
from io import BytesIO
import base64
import sqlite3
from uuid import uuid4

from PIL import Image

from tests.test_purchase_record_http_restart import server
from tests.test_postgres_full_api_optin import register
from tests.test_seller_ratings_http import purchase, collect


def test_demo_purchase_pin_rating_wallet_ad(tmp_path, monkeypatch):
    monkeypatch.setenv('WP_ENABLE_WALLET_PREVIEW', '1')
    path = tmp_path / 'demo_end_to_end.sqlite3'
    with server(path) as client:
        seller, seller_id = register(client, 'rolnik')
        buyer, buyer_id = register(client, 'klient')
        admin, admin_id = register(client, 'klient')
        with closing(sqlite3.connect(path)) as con:
            con.execute("UPDATE users SET role='admin' WHERE id=?", (admin_id,))
            con.commit()

        img = BytesIO()
        Image.new('RGB', (300, 150), 'blue').save(img, 'PNG')
        now = datetime.now(timezone.utc).replace(microsecond=0)
        campaign = {
            'advertiser': 'Testowa reklama demo',
            'url': 'https://example.org/demo',
            'image_base64': base64.b64encode(img.getvalue()).decode(),
            'starts_at': (now - timedelta(hours=1)).isoformat(),
            'ends_at': (now + timedelta(days=1)).isoformat(),
            'enabled': True,
            'sort_order': 0,
        }
        created = client.post('/admin/wallet-ads', headers=admin, json=campaign)
        assert created.status_code == 201, created.text

        order = purchase(client, buyer, seller)
        rating_url = f"/orders/{order['id']}/seller-rating"
        assert client.post(rating_url, headers=buyer, json={'stars': 5}).status_code == 409
        collect(client, buyer, seller, order)
        rated = client.post(rating_url, headers=buyer, json={'stars': 5})
        assert rated.status_code == 200, rated.text
        assert rated.json()['already_rated'] is False
        assert client.get(f'/farmers/{seller_id}/ratings').json()['average'] == 5

        wallet_before = client.get('/wallet', headers=buyer)
        assert wallet_before.status_code == 200, wallet_before.text
        key = uuid4().hex
        first = client.post('/wallet/ads/claim', headers=buyer, json={'request_key': key})
        assert first.status_code == 200, first.text
        assert first.json()['ad']['duration_seconds'] == 5
        assert client.post('/wallet/ads/claim', headers=buyer,
                           json={'request_key': uuid4().hex}).json() == {'ad': None}
        assert client.get('/wallet', headers=buyer).json() == wallet_before.json()

        # A separate seller account has its own 30-minute advertisement cap.
        seller_ad = client.post('/wallet/ads/claim', headers=seller,
                                json={'request_key': uuid4().hex})
        assert seller_ad.status_code == 200
        assert seller_ad.json()['ad'] is not None
        assert client.get(f'/farmers/{seller_id}/ratings').json()['count'] == 1

    # The same database survives restart; ratings and ad cooldown persist.
    with server(path) as client:
        assert client.get(f'/farmers/{seller_id}/ratings').json()['count'] == 1
        again = client.post('/wallet/ads/claim', headers=buyer,
                            json={'request_key': uuid4().hex})
        assert again.status_code == 200
        assert again.json() == {'ad': None}
