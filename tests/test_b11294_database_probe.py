import pytest
from backend.test_server_launcher import verify_test_database_connection


class Cursor:
    def __init__(self, name): self.name = name
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql):
        assert sql == 'SELECT current_database()'
    def fetchone(self): return (self.name,) if self.name is not None else None


class Connection:
    def __init__(self, name): self.name = name; self.closed = False
    def cursor(self): return Cursor(self.name)
    def close(self): self.closed = True


@pytest.mark.parametrize('name,expected,success', [
    ('wp_test','wp_test',True), ('production','wp_test',False),
    (None,'wp_test',False), ('WP_TEST','wp_test',False),
])
def test_probe(name, expected, success):
    connection = Connection(name)
    def connect(dsn, **kwargs):
        assert dsn == 'postgresql://test/db'
        assert kwargs == {'connect_timeout': 5}
        return connection
    if success:
        verify_test_database_connection('postgresql://test/db', expected, connect)
    else:
        with pytest.raises(ValueError):
            verify_test_database_connection('postgresql://test/db', expected, connect)
    assert connection.closed


def test_connection_failure_propagates():
    def fail(*args, **kwargs): raise ConnectionError('unavailable')
    with pytest.raises(ConnectionError):
        verify_test_database_connection('postgresql://test/db', 'wp_test', fail)


def test_query_failure_still_closes():
    connection = Connection('wp_test')
    def bad_cursor(): raise RuntimeError('query failed')
    connection.cursor = bad_cursor
    with pytest.raises(RuntimeError):
        verify_test_database_connection('postgresql://test/db', 'wp_test', lambda *a, **kw: connection)
    assert connection.closed
