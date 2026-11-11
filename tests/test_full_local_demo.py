"""Real complete sample setup, hostile inherited environment and local HTTP."""
from pathlib import Path
import json
import os
import subprocess
import sys
import pytest
from scripts.run_phone_demo import full_demo_environment,FULL_DEMO_FLAGS,main
from tests.test_purchase_record_http_restart import server
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def test_full_demo_does_not_inherit_outgoing_services_or_secrets(tmp_path):
    source={'PATH':os.environ['PATH'],'DATABASE_URL':'postgresql://private.invalid/live',
            'WP_ENABLE_ORDER_SMTP':'1','WP_SMTP_PASSWORD':'private',
            'WP_ENABLE_VERIFICATION_SMTP':'1','WP_ENABLE_ORDER_MAIL_QUEUE':'1',
            'WP_MAIL_QUEUE_KEYS_FILE':'/private/keys','PAYU_CLIENT_SECRET':'private',
            'PGPASSWORD':'private','WP_ENV':'production','PYTHONPATH':'/untrusted'}
    env=full_demo_environment(source,tmp_path/'fresh.sqlite3')
    assert all(env[flag]=='1' for flag in FULL_DEMO_FLAGS)
    assert env['WP_ENV']=='development' and env['WP_ENABLE_TEST_PAYMENTS']=='1'
    assert not set(source).difference({'PATH','WP_ENV'}).intersection(env)
    assert 'private' not in json.dumps(env)


@pytest.mark.parametrize('geocoder', [False, True])
def test_full_profile_launcher_seeds_all_roles_and_preserves_options(tmp_path,monkeypatch,capsys,geocoder):
    monkeypatch.setenv('WP_ENABLE_ORDER_SMTP','1')
    seen=[]
    def launch(command,**kwargs):
        env=kwargs['env'];seen.append(Path(env['WIEJSKAPAKA_DB']))
        assert all(env[flag]=='1' for flag in FULL_DEMO_FLAGS)
        assert 'WP_ENABLE_ORDER_SMTP' not in env
        assert command[command.index('--host')+1]=='127.0.0.1'
        with patch.dict(os.environ,env,clear=True),server(seen[-1], address_search_url=env.get('WP_ADDRESS_SEARCH_URL')) as client:
            assert client.get('/address-search/config').json()['enabled'] is geocoder
            for endpoint in ('/sellers/config','/product-units','/pickup-point-dates/config','/address-delivery/config'):
                r=client.get(endpoint)
                assert r.status_code==200 and r.json()['enabled']
            assert len(client.get('/products').json())==2
            assert client.get('/sellers/search?q=gospodarstwo_demo').json()['items']
            # Credentials are purposely not exposed by public pages.
            assert client.get('/wallet').status_code==401
        return 0
    with patch('scripts.run_phone_demo.subprocess.call',side_effect=launch):
        assert main(['--full-demo'] + (['--address-search-url', 'https://geo.invalid/search'] if geocoder else []))==0
    assert seen and not seen[0].exists()
    assert 'private' not in capsys.readouterr().out
