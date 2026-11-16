"""Same HTTP contract with FORCE RLS and a restricted real PostgreSQL login."""
import os
import pytest
from tests.test_postgres_full_api_optin import pg_wallet_api,register,inspection_connect
from tests.test_wallet_ads_http import exercise,DEVICE_PASSWORD

pytestmark=pytest.mark.skipif(os.environ.get('WP_TEST_ENABLE_RLS')!='1',reason='Run local RLS gate')


def test_wallet_ads_rls_atomic_account_isolation_and_admin(pg_wallet_api):
    client,parameters=pg_wallet_api
    buyer,uid=register(client,'klient',password=DEVICE_PASSWORD);seller,_=register(client,'rolnik');other,_=register(client,'klient');admin,aid=register(client,'klient')
    with inspection_connect(**parameters) as con:con.execute("UPDATE users SET role='admin' WHERE id=%s",(aid,))
    def expire():
        with inspection_connect(**parameters) as con:con.execute('UPDATE wallet_ad_accounts SET last_shown=last_shown-1801 WHERE user_id=%s',(uid,))
    exercise(client,admin,buyer,seller,other,expire)
