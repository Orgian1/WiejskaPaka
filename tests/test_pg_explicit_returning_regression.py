"""Explicit RETURNING must not be silently consumed by the SQLite adapter."""
from backend.pg_adapter import PgConnection


class FakeCursor:
    rowcount = 1

    def __init__(self, rows):
        self.rows = list(rows)

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    def execute(self, sql, params):
        self.statements.append((sql, params))
        return FakeCursor(self.rows)


def test_explicit_returning_id_remains_fetchable():
    connection = FakeConnection([{'id': 19}])
    cursor = PgConnection(connection).execute('INSERT INTO users(email) VALUES (?) RETURNING id', ('a',))
    assert cursor.lastrowid is None
    assert cursor.fetchone() == {'id': 19}
    assert cursor.fetchone() is None


def test_explicit_returning_multiple_columns_remains_fetchable():
    connection = FakeConnection([{'id': 19, 'email': 'a'}])
    cursor = PgConnection(connection).execute(
        'INSERT INTO users(email) VALUES (?) RETURNING id, email', ('a',)
    )
    assert cursor.fetchall() == [{'id': 19, 'email': 'a'}]


def test_automatically_added_returning_populates_lastrowid():
    connection = FakeConnection([{'id': 20}])
    cursor = PgConnection(connection).execute('INSERT INTO users(email) VALUES (?)', ('b',))
    assert connection.statements[0][0].endswith('RETURNING id')
    assert cursor.lastrowid == 20
    assert cursor.fetchone() is None


def test_insert_without_generated_id_does_not_consume_result():
    connection = FakeConnection([])
    cursor = PgConnection(connection).execute(
        'INSERT INTO farmer_profiles(user_id) VALUES (?) ON CONFLICT(user_id) DO NOTHING', (1,)
    )
    assert cursor.lastrowid is None
