"""PostgreSQL placeholder translation regression tests; no live DB required."""
import pytest
from backend.pg_adapter import translate_sql

@pytest.mark.parametrize('sql,expected', [
    ('SELECT ? -- ? in comment', 'SELECT %s -- ? in comment'),
    ('SELECT ? /* ? in comment */ , ?', 'SELECT %s /* ? in comment */ , %s'),
    ('SELECT ? /* outer /* nested ? */ still ? */ , ?', 'SELECT %s /* outer /* nested ? */ still ? */ , %s'),
    ('SELECT $$?$$, ?', 'SELECT $$?$$, %s'),
    ('SELECT $abc$? ?$abc$, ?', 'SELECT $abc$? ?$abc$, %s'),
    ('SELECT "col?", ?', 'SELECT "col?", %s'),
    ("SELECT 'it''s ?' AS s, ?", "SELECT 'it''s ?' AS s, %s"),
    ('SELECT ? -- ?\n, ?', 'SELECT %s -- ?\n, %s'),
    ('SELECT ? /* ? */ -- ?\n, ?', 'SELECT %s /* ? */ -- ?\n, %s'),
    ('SELECT $x$ -- ? /* ? */ $x$, ?', 'SELECT $x$ -- ? /* ? */ $x$, %s'),
    ('BEGIN IMMEDIATE;', None),
    ('INSERT INTO users(email) VALUES(?);', 'INSERT INTO users(email) VALUES(%s) RETURNING id;'),
])
def test_translate_does_not_modify_non_placeholders(sql, expected):
    assert translate_sql(sql) == expected


def test_untrusted_values_are_bound_not_interpolated():
    query = translate_sql('SELECT * FROM users WHERE email=?')
    assert query == 'SELECT * FROM users WHERE email=%s'
