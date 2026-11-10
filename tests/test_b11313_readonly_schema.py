"""Verify the schema gate never permits database writes during inspection."""
from database.verify_migrated_schema import verify_schema
from backend.postgres_schema_preflight import CORE_TABLES
from database.verify_migrated_schema import STARTUP_COLUMNS

# Self-contained synthetic fixture: the previous import referenced a local-only
# test module intentionally excluded from the repository.
ENV = {'WP_ENV': 'test', 'WP_TEST_DATABASE_URL': 'postgresql://localhost/wp_test_11312',
       'WP_BIND_HOST': '127.0.0.1'}

def make_rows():
    return [(table, column) for table in CORE_TABLES
            for column in STARTUP_COLUMNS.get(table, {'id'})]

class Cursor:
    def __init__(self):
        self.commands = []
    def execute(self, sql, *args):
        self.commands.append(sql)
    def fetchone(self):
        if self.commands[-1].startswith('SELECT current_database'): return ('wp_test_11312',)
        return (False, False, False, False)
    def fetchall(self): return make_rows()
    def __enter__(self): return self
    def __exit__(self, *args): return False

class Connection:
    def __init__(self): self.cur = Cursor(); self.closed = False
    def cursor(self): return self.cur
    def close(self): self.closed = True

def test_read_only_before_any_probe():
    con = Connection()
    assert verify_schema(ENV, lambda *a, **k: con)['ok']
    assert con.cur.commands[0] == 'SET TRANSACTION READ ONLY'
    assert all(cmd.startswith('SELECT ') for cmd in con.cur.commands[1:])
    assert con.closed
