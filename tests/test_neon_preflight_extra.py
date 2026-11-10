"""Regression tests for safe preparation before an external Neon database exists."""
import sqlite3
import pytest
from database.migration_plan import build_plan
from database.migrate_all_tables import validate_plan, destination_tables_to_check


def test_missing_destination_table_even_when_source_empty(tmp_path):
    path = tmp_path / 'source.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE customers (id INTEGER PRIMARY KEY, email TEXT)')
    plan = build_plan(path, {})
    assert plan['tables']['customers']['rows'] == 0
    with pytest.raises(ValueError, match='Brak tabeli docelowej'):
        validate_plan(plan)


def test_missing_destination_column_is_blocker(tmp_path):
    path = tmp_path / 'source.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE orders (id INTEGER PRIMARY KEY, amount_grosze INTEGER NOT NULL)')
        db.execute('INSERT INTO orders (amount_grosze) VALUES (125)')
    plan = build_plan(path, {'orders': {'id'}})
    with pytest.raises(ValueError, match='Brak mapowania'):
        validate_plan(plan)


def test_foreign_key_order(tmp_path):
    path = tmp_path / 'source.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE parent (id INTEGER PRIMARY KEY)')
        db.execute('CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id))')
    plan = build_plan(path, {'parent': {'id'}, 'child': {'id', 'parent_id'}})
    assert plan['copy_order'].index('parent') < plan['copy_order'].index('child')


def test_destination_checks_extra_tables():
    assert destination_tables_to_check({'users': {'id'}, 'audit': {'id'}}, ['users']) == ['audit', 'users']


def test_no_sqlite_file_created_when_missing(tmp_path):
    missing = tmp_path / 'absent.db'
    with pytest.raises(ValueError, match='nie istnieje'):
        build_plan(missing, {})
    assert not missing.exists()
