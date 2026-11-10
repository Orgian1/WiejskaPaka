"""Regresje kompatybilności składni SQLite -> PostgreSQL."""
from backend.pg_adapter import PgConnection, translate_sql


def test_returning_before_semicolon():
    assert translate_sql('INSERT INTO users(email, password_hash, role) VALUES (?, ?, ?);') == (
        'INSERT INTO users(email, password_hash, role) VALUES (%s, %s, %s) RETURNING id;'
    )


def test_existing_returning_not_duplicated():
    sql = 'INSERT INTO orders(buyer_id) VALUES (?) RETURNING id;'
    assert translate_sql(sql) == sql.replace('?', '%s')


def test_literal_question_mark_is_not_parameter():
    assert translate_sql("SELECT '?' AS literal, ? AS parameter") == "SELECT '?' AS literal, %s AS parameter"


def test_returning_with_semicolon_sets_lastrowid():
    class Cursor:
        rowcount = 1
        def fetchone(self):
            return {'id': 73}
    class Connection:
        def execute(self, sql, params):
            assert sql.endswith('RETURNING id;')
            return Cursor()
    result = PgConnection(Connection()).execute('INSERT INTO users(email) VALUES (?);', ('x',))
    assert result.lastrowid == 73
