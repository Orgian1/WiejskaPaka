"""Temporary demo creatives must disappear when real advertising starts."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import sqlite3

from tests.test_purchase_record_http_restart import server
from tests.test_postgres_full_api_optin import register
from tests.test_wallet_ads_http import campaign, claim
from scripts.demo_ad_banners import make_banner


def test_banner_artwork_is_valid_jpeg():
    import base64
    for role in ('klient', 'rolnik'):
        raw = base64.b64decode(make_banner(role), validate=True)
        assert raw.startswith(bytes.fromhex('ffd8ff'))
        assert len(raw) < 1_000_000


def test_placeholder_retires_only_when_matching_real_campaign_enabled(tmp_path):
    path = tmp_path / 'temporary.sqlite3'
    with server(path) as client:
        buyer, _ = register(client, 'klient')
        farmer, _ = register(client, 'rolnik')
        admin, admin_id = register(client, 'klient')
        with closing(sqlite3.connect(path)) as con:
            con.execute("UPDATE users SET role='admin' WHERE id=?", (admin_id,))
            con.commit()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        ids = {}
        for audience in ('klient', 'rolnik'):
            body = campaign()
            body.update(advertiser='WiejskaPaka - miejsce na reklamę',
                        url='https://example.invalid/wiejskapaka-demo-placeholder-' + audience,
                        audience=audience, sort_order=100000)
            result = client.post('/admin/wallet-ads', headers=admin, json=body)
            assert result.status_code == 201, result.text
            ids[audience] = result.json()['id']
        assert claim(client, buyer).json()['ad']['id'] == ids['klient']
        assert claim(client, farmer).json()['ad']['id'] == ids['rolnik']
        real = campaign()
        real.update(audience='klient', enabled=False)
        created = client.post('/admin/wallet-ads', headers=admin, json=real)
        assert created.status_code == 201, created.text
        listing = client.get('/admin/wallet-ads', headers=admin).json()['items']
        assert any(x['id'] == ids['klient'] for x in listing)
        real['enabled'] = True
        updated = client.put('/admin/wallet-ads/' + created.json()['id'], headers=admin, json=real)
        assert updated.status_code == 200, updated.text
        listing = client.get('/admin/wallet-ads', headers=admin).json()['items']
        assert not any(x['id'] == ids['klient'] for x in listing)
        assert any(x['id'] == ids['rolnik'] for x in listing)
        with closing(sqlite3.connect(path)) as con:
            con.execute('UPDATE wallet_ad_accounts SET last_shown=0')
            con.commit()
        assert claim(client, buyer).json()['ad']['id'] == created.json()['id']
        assert claim(client, farmer).json()['ad']['id'] == ids['rolnik']
