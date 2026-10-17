import sqlite3
import pytest
from database.migrate_all_tables import validate_plan, copy_all, destination_structure_from_cursor


def test_blocks_missing_nonempty_table():
    with pytest.raises(ValueError, match='Brak mapowania'):
        validate_plan({'blocked_nonempty_tables': ['orders']})


def test_blocks_missing_empty_table_too():
    with pytest.raises(ValueError, match='Tabela'):
        validate_plan({'blocked_nonempty_tables': [], 'tables': {'x': {'blockers': ['brak'], 'rows': 0}}, 'copy_order': ['x']})


def test_blocks_cycles():
    with pytest.raises(ValueError, match='Cykl'):
        validate_plan({'blocked_nonempty_tables': [], 'tables': {'a': {'blockers': [], 'rows': 1}}, 'copy_order': []})


def test_requires_explicit_execute():
    with pytest.raises(ValueError, match='potwierdzenie'):
        copy_all('/no/file', 'no-dsn')


def test_accepts_simple_plan():
    assert validate_plan({'blocked_nonempty_tables': [], 'tables': {'a': {'blockers': [], 'rows': 2}}, 'copy_order': ['a']})


def test_structure_from_cursor():
    class Cursor:
        def execute(self, sql):
            assert 'information_schema.columns' in sql
        def fetchall(self):
            return [('users', 'id'), ('users', 'email'), ('orders', 'id')]
    assert destination_structure_from_cursor(Cursor()) == {'users': {'id', 'email'}, 'orders': {'id'}}
