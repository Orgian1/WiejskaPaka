"""Migration plan and copy must use the same SQLite snapshot."""
import sqlite3

from database.migration_plan import build_plan


def test_planner_uses_provided_snapshot(tmp_path):
    path = tmp_path / 'source.db'
    with sqlite3.connect(path) as con:
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT)')
        con.execute("INSERT INTO products VALUES (1, 'jabłka')")
    source = sqlite3.connect(path, isolation_level=None)
    try:
        source.execute('BEGIN')
        assert source.execute('SELECT count(*) FROM products').fetchone()[0] == 1
        with sqlite3.connect(path) as writer:
            writer.execute("INSERT INTO products VALUES (2, 'gruszki')")
        plan = build_plan(path, {'products': {'id', 'name'}}, source_connection=source)
        assert plan['tables']['products']['rows'] == 1
        assert source.execute('SELECT count(*) FROM products').fetchone()[0] == 1
    finally:
        source.close()


def test_planner_does_not_close_supplied_connection(tmp_path):
    path = tmp_path / 'source.db'
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE items (id INTEGER PRIMARY KEY)')
    con = sqlite3.connect(path)
    try:
        build_plan(path, {'items': {'id'}}, source_connection=con)
        assert con.execute('SELECT 1').fetchone()[0] == 1
    finally:
        con.close()
