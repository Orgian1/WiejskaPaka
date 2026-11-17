"""Regression: separate wallet ad audiences must never cross roles."""
from contextlib import closing
import sqlite3
from uuid import uuid4

from tests.test_purchase_record_http_restart import server
from tests.test_postgres_full_api_optin import register
from tests.test_wallet_ads_http import campaign, claim


def test_wallet_ad_audience_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv('WP_ENABLE_WALLET_PREVIEW', '1')
    path = tmp_path / 'audiences.sqlite3'
    with server(path) as client:
        buyer, _ = register(client, 'klient')
        seller, _ = register(client, 'rolnik')
        admin, admin_id = register(client, 'klient')
        with closing(sqlite3.connect(path)) as con:
            con.execute("UPDATE users SET role='admin' WHERE id=?", (admin_id,))
            con.commit()

        customer = campaign()
        customer['audience'] = 'klient'
        customer['advertiser'] = 'Reklama klienta'
        r = client.post('/admin/wallet-ads', headers=admin, json=customer)
        assert r.status_code == 201, r.text
        customer_id = r.json()['id']

        farmer = campaign()
        farmer['audience'] = 'rolnik'
        farmer['advertiser'] = 'Reklama sprzedawcy'
        r = client.post('/admin/wallet-ads', headers=admin, json=farmer)
        assert r.status_code == 201, r.text
        farmer_id = r.json()['id']

        buyer_ad = claim(client, buyer).json()['ad']
        seller_ad = claim(client, seller).json()['ad']
        assert buyer_ad and buyer_ad['id'] == customer_id
        assert seller_ad and seller_ad['id'] == farmer_id
        assert buyer_ad['id'] != seller_ad['id']
        assert claim(client, buyer).json() == {'ad': None}
        assert claim(client, seller).json() == {'ad': None}

        invalid = campaign()
        invalid['audience'] = 'admin'
        assert client.post('/admin/wallet-ads', headers=admin, json=invalid).status_code == 422
