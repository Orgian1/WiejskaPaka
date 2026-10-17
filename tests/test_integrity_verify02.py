import sqlite3
import pytest
from backend.data_integrity import inspect_sqlite


def test_clean_database(tmp_path):
    p = tmp_path / 'clean.sqlite'
    with sqlite3.connect(p) as con:
        con.execute('CREATE TABLE parent(id INTEGER PRIMARY KEY)')
        con.execute('CREATE TABLE child(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id))')
        con.execute('INSERT INTO parent VALUES (1)')
        con.execute('INSERT INTO child VALUES (1,1)')
    report = inspect_sqlite(p)
    assert report['ok'] is True
    assert report['row_counts']['child'] == 1


def test_orphan_is_detected(tmp_path):
    p = tmp_path / 'orphan.sqlite'
    with sqlite3.connect(p) as con:
        con.execute('CREATE TABLE parent(id INTEGER PRIMARY KEY)')
        con.execute('CREATE TABLE child(parent_id INTEGER REFERENCES parent(id))')
        con.execute('INSERT INTO child VALUES (999)')
    report = inspect_sqlite(p)
    assert report['ok'] is False
    assert report['foreign_key_violations'][0]['parent'] == 'parent'


def test_missing_file_not_created(tmp_path):
    p = tmp_path / 'missing.sqlite'
    with pytest.raises(FileNotFoundError):
        inspect_sqlite(p)
    assert not p.exists()


def test_audit_does_not_modify_file(tmp_path):
    p = tmp_path / 'read_only.sqlite'
    with sqlite3.connect(p) as con:
        con.execute('CREATE TABLE t(id INTEGER)')
    before = p.read_bytes()
    inspect_sqlite(p)
    assert p.read_bytes() == before
