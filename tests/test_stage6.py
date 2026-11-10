import sqlite3
from pathlib import Path
import pytest
from database.migrate_sqlite_to_postgres import read_source, TABLES

def test_source_validation(tmp_path):
    path=tmp_path/'db.sqlite3'
    con=sqlite3.connect(path)
    for table in TABLES:
        con.execute(f'CREATE TABLE {table}(id INTEGER)')
    con.commit(); con.close()
    data=read_source(path)
    assert all(not rows for rows in data.values())

def test_missing_tables(tmp_path):
    path=tmp_path/'db.sqlite3'
    sqlite3.connect(path).close()
    with pytest.raises(ValueError, match='Brak tabel'):
        read_source(path)

def test_missing_file(tmp_path):
    with pytest.raises(ValueError, match='Nie znaleziono'):
        read_source(tmp_path/'none.sqlite3')

def test_schema_has_money_and_integrity_constraints():
    schema=(Path(__file__).parents[1]/'database/postgres_schema.sql').read_text()
    assert 'BIGINT NOT NULL CHECK(price_grosze>=1)' in schema
    assert 'total_grosze=subtotal_grosze+delivery_grosze' in schema
    assert 'CHECK(pin_attempts BETWEEN 0 AND 5)' in schema
