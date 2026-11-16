"""Native PostgreSQL/FORCE RLS HTTP contract and aggregate privacy."""
import os
import pytest
from tests.test_postgres_full_api_optin import pg_api,inspection_connect
from tests.test_seller_ratings_http import exercise

pytestmark=pytest.mark.skipif(os.environ.get('WP_TEST_ENABLE_RLS')!='1',reason='Run local RLS gate')


def test_seller_ratings_actual_postgres_rls(pg_api):
    client,parameters=pg_api
    sid=exercise(client)
    with inspection_connect(**parameters) as con:
        flags=con.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='seller_ratings'::regclass").fetchone()
        assert flags==(True,True)
    assert client.get(f'/farmers/{sid}/ratings').json()['count']==2
