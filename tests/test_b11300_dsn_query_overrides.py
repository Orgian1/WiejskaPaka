"""A validated database URL must not be redirected by libpq query overrides."""
import pytest
from backend.test_server_preflight import check_test_server


def config(query=''):
    return {'WP_ENV': 'test', 'WP_TEST_DATABASE_URL':
            'postgresql://tester@localhost/wp_test' + query}


@pytest.mark.parametrize('query', [
    '?host=production.example', '?HOST=production.example',
    '?hostaddr=10.0.0.1', '?port=5433', '?dbname=production',
    '?database=production', '?user=postgres', '?password=secret',
    '?service=production', '?servicefile=/tmp/service',
    '?passfile=/tmp/password', '?options=-c%20search_path%3Dother',
    '?requiressl=0', '?sslrootcert=/tmp/ca', '?sslcert=/tmp/client',
    '?sslkey=/tmp/key', '?sslpassword=x',
    '?connect_timeout=5&connect_timeout=1',
    '?sslmode=verify-full&SSLMODE=disable',
])
def test_reject_query_overrides(query):
    with pytest.raises(ValueError):
        check_test_server(config(query))


@pytest.mark.parametrize('query', ['', '?connect_timeout=5', '?sslmode=verify-full',
                                   '?application_name=wp_test&connect_timeout=5'])
def test_safe_query_parameters(query):
    assert check_test_server(config(query))['database_name'] == 'wp_test'
