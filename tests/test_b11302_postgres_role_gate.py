"""No privileged PostgreSQL runtime role on the private test listener."""
import pytest
from backend.postgres_schema_preflight import CORE_TABLES
from backend.test_server_launcher import verify_test_database_connection

class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.query = ''
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, query, params=None):
        self.query = query
        if 'information_schema.tables' in query:
            assert params == ('public', 'BASE TABLE', list(CORE_TABLES))
    def fetchone(self):
        if 'current_database()' in self.query: return ('wp_test',)
        if 'pg_roles' in self.query: return self.connection.flags
        raise AssertionError(self.query)
    def fetchall(self): return [(name,) for name in CORE_TABLES]

class Connection:
    def __init__(self, flags): self.flags = flags; self.closed = False
    def cursor(self): return Cursor(self)
    def close(self): self.closed = True

@pytest.mark.parametrize('flags', [
    (True, False, False, False), (False, True, False, False),
    (False, False, True, False), (False, False, False, True),
    None, (), (0, False, False, False), ('f', False, False, False),
    (False, None, False, False),
])
def test_privileged_or_ambiguous_role_rejected_and_closed(flags):
    connection = Connection(flags)
    with pytest.raises(RuntimeError, match='non-privileged'):
        verify_test_database_connection('unused', 'wp_test', connect=lambda *a, **kw: connection,
                                        require_schema=True)
    assert connection.closed

def test_unprivileged_role_passes_and_closes():
    connection = Connection((False, False, False, False))
    verify_test_database_connection('unused', 'wp_test', connect=lambda *a, **kw: connection,
                                    require_schema=True)
    assert connection.closed
