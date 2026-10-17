"""Regresja: migracja nie może milcząco pominąć danych modułów."""
import sqlite3
import pytest
from database.migrate_sqlite_to_postgres import TABLES, read_source


def create_source(path):
    con = sqlite3.connect(path)
    for name in TABLES:
        con.execute(f'CREATE TABLE "{name}" (id INTEGER PRIMARY KEY)')
    con.commit()
    return con


def test_migration_refuses_nonempty_extra_table(tmp_path):
    path = tmp_path / 'source.sqlite3'
    con = create_source(path)
    con.execute('CREATE TABLE seller_compliance (id INTEGER PRIMARY KEY)')
    con.execute('INSERT INTO seller_compliance VALUES (1)')
    con.commit()
    con.close()
    with pytest.raises(ValueError, match='ryzyko utraty danych'):
        read_source(path)


def test_migration_allows_empty_extra_table(tmp_path):
    path = tmp_path / 'source.sqlite3'
    con = create_source(path)
    con.execute('CREATE TABLE seller_compliance (id INTEGER PRIMARY KEY)')
    con.commit()
    con.close()
    assert set(read_source(path)) == set(TABLES)


def test_migration_refuses_missing_file(tmp_path):
    with pytest.raises(ValueError, match='Nie znaleziono'):
        read_source(tmp_path / 'missing.sqlite3')
