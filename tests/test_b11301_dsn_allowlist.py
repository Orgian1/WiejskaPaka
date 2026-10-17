"""Allowlist unknown libpq URL options rather than relying on a blacklist."""
import pytest
from backend.test_server_preflight import check_test_server


def config(query):
    return {'WP_ENV': 'test', 'WP_TEST_DATABASE_URL': 'postgresql://tester@localhost/wp_test' + query}


@pytest.mark.parametrize('query', [
    '?target_session_attrs=read-write', '?load_balance_hosts=random',
    '?gssencmode=disable', '?krbsrvname=postgres', '?channel_binding=disable',
    '?keepalives=0', '?fallback_application_name=prod', '?sslnegotiation=direct',
    '?foo=bar', '?connect_timeout=0', '?connect_timeout=31',
    '?connect_timeout=-1', '?connect_timeout=1.5', '?connect_timeout=%D9%A1',
    '?application_name=bad%20name', '?application_name=%0A',
    '?application_name=', '?application_name=1starts_with_number',
    '?application_name=' + 'x'*64,
])
def test_reject_unreviewed_or_invalid_options(query):
    with pytest.raises(ValueError):
        check_test_server(config(query))


@pytest.mark.parametrize('query', [
    '', '?connect_timeout=1', '?connect_timeout=30',
    '?application_name=wp-test_01', '?sslmode=verify-full',
    '?connect_timeout=5&application_name=WiejskaPaka_test',
])
def test_accept_audited_options(query):
    assert check_test_server(config(query))['database_name'] == 'wp_test'
